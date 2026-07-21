from decimal import Decimal
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models.functions import Coalesce
from django.db.models import DecimalField, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from core.workflow import WorkflowRegistry
from core.workflow_service import WorkflowService
from orders.models import Order as EnterpriseOrder
from .dashboard import FurnitureDashboard
from django.shortcuts import redirect, render
from .models import ProductionSettings
from .forms import (
    AssignWorkerForm,
    OrderForm,
    ProductionChecklistForm,
    ProductionJobForm,
    ProductionLabourForm,
    ProductionMachineForm,
    ProductionMaterialForm,
    ProductionOutputForm,
    ProductionTaskActionForm,
    ProductionTaskAssignmentForm,
    ProductionTaskBlockForm,
    ProductionTaskForm,
    ProductionTaskProgressForm,
    QuotationForm,
    ProductionSettingsForm,
    QualityInspectionForm,
    QualityInspectionResultForm,
    ProductionDefectForm,
    ReworkOrderForm,
    ReworkCompletionForm,
    ReworkVerificationForm,
)
from .models import (
    Order as LegacyOrder,
    ProductionChecklist,
    ProductionJob,
    ProductionLabour,
    ProductionMachine,
    ProductionMaterial,
    ProductionOutput,
    ProductionTask,
    ProductionTimeline,
    Quotation,
    QualityInspection,
    ProductionDefect,
    ReworkOrder,
    
)
from .services import (
    ProductionService,
    ProductionTaskService,
    QuotationService,
    ProductionCostService,
    QualityService,
    PlanningService
)



# =====================================================
# HELPERS
# =====================================================


def _employee_for_user(user):
    """Return the Employee linked to a User, or None safely."""
    if not user or not user.is_authenticated:
        return None

    try:
        return user.employee
    except (AttributeError, ObjectDoesNotExist):
        return None


def _validation_message(error):
    if hasattr(error, "messages"):
        return "; ".join(error.messages)
    return str(error)


# =====================================================
# DASHBOARD
# =====================================================


@login_required
def furniture_dashboard(request):
    return render(
        request,
        "furniture/dashboard.html",
        FurnitureDashboard.get_context(request.user),
    )


# =====================================================
# LEGACY FURNITURE ORDERS
# Keep only while migrating to orders.Order
# =====================================================


@login_required
def order_list(request):
    orders = LegacyOrder.objects.select_related(
        "product",
        "assigned_to",
        "created_by",
    ).order_by("-created_at")

    return render(
        request,
        "furniture/order_list.html",
        {"orders": orders},
    )


@login_required
def order_create(request):
    form = OrderForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        order.created_by = _employee_for_user(request.user)
        order.save()

        messages.success(request, "Customer order created successfully.")
        return redirect("furniture:order_list")

    return render(
        request,
        "furniture/order_form.html",
        {"form": form},
    )


@login_required
def assign_worker(request, pk):
    order = get_object_or_404(LegacyOrder, pk=pk)
    form = AssignWorkerForm(request.POST or None, instance=order)

    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        order.status = "assigned"
        order.save()

        messages.success(request, "Worker assigned successfully.")
        return redirect("furniture:order_list")

    return render(
        request,
        "furniture/assign_worker.html",
        {"form": form, "order": order},
    )


# =====================================================
# ORDER ENGINE -> PRODUCTION JOB
# =====================================================


@login_required
@require_POST
def create_production_job(request, order_id):
    order = get_object_or_404(EnterpriseOrder, pk=order_id)

    if hasattr(order, "production_job"):
        messages.info(request, "This order already has a production job.")
        return redirect(
            "furniture:production_job_detail",
            pk=order.production_job.pk,
        )

    employee = _employee_for_user(request.user)
    product = getattr(order, "product", None)
    quantity = (
        getattr(order, "quantity", None)
        or getattr(order, "quantity_to_produce", None)
        or 1
    )

    try:
        job = ProductionService.create_job(
            order=order,
            product=product,
            job_type="CUSTOMER_CUSTOM",
            quantity_to_produce=quantity,
            created_by=employee,
            description=getattr(order, "description", "") or "",
        )
    except ValidationError as error:
        messages.error(request, _validation_message(error))
        return redirect("orders:order_detail", pk=order.pk)

    messages.success(request, "Production job created successfully.")
    return redirect("furniture:production_job_detail", pk=job.pk)


# =====================================================
# PRODUCTION JOBS
# =====================================================


@login_required
def production_job_list(request):
    jobs = ProductionJob.objects.select_related(
        "order",
        "product",
        "assigned_to",
        "created_by",
    ).order_by("-created_at")

    status = request.GET.get("status")
    if status:
        jobs = jobs.filter(status=status.upper())

    return render(
        request,
        "furniture/production_job_list.html",
        {
            "jobs": jobs,
            "status_choices": ProductionJob.STATUS,
            "selected_status": status or "",
        },
    )


@login_required
def production_job_detail(request, pk):
    job = get_object_or_404(
        ProductionJob.objects.select_related(
            "product",
            "assigned_to",
            "created_by",
            "order",
        ).prefetch_related(
            "tasks__assigned_to",
            "tasks__checklist_items",
            "tasks__progress_updates",
            "materials__raw_material",
            "labours__employee",
            "machines__asset",
            "outputs__product",
            "timeline",
        ),
        pk=pk,
    )

    active_tasks = job.tasks.exclude(
        status="CANCELLED"
    )

    total_tasks = active_tasks.count()

    completed_tasks_count = active_tasks.filter(
        status="COMPLETED"
    ).count()
    cost_summary = ProductionCostService.job_cost_summary(
        production_job=job,
        overhead_rate=Decimal("10.00"),
        wastage_rate=Decimal("5.00"),
        transport_cost=Decimal("5000.00"),
        other_cost=Decimal("1000.00"),
    )

    if total_tasks:
        overall_progress = round(
            sum(
                task.progress_percentage
                for task in active_tasks
            ) / total_tasks,
            2,
        )
    else:
        overall_progress = 0

    inspection = (
        QualityInspection.objects
        .filter(production_job=job)
        .select_related(
            "inspector",
            "approved_by",
        )
        .prefetch_related("defects")
        .order_by("-created_at")
        .first()
    )

    return render(
        request,
        "furniture/production_job_detail.html",
        {
            "job": job,
            "overall_progress": overall_progress,
            "completed_tasks_count": completed_tasks_count,
            "cost_summary": cost_summary,
            "inspection" :inspection
        },
    )

@login_required
def production_job_create(request):
    selected_order_id = request.GET.get("order")

    if selected_order_id:
        existing_job = (
            ProductionJob.objects
            .filter(order_id=selected_order_id)
            .first()
        )

        if existing_job:
            messages.info(
                request,
                (
                    "This customer order already has "
                    "a production job."
                ),
            )

            return redirect(
                "furniture:production_job_detail",
                pk=existing_job.pk,
            )

    initial = {}

    if selected_order_id:
        initial["order"] = selected_order_id

    if request.method == "POST":
        form = ProductionJobForm(
            request.POST
        )

        if form.is_valid():
            data = form.cleaned_data

            employee = _employee_for_user(
                request.user
            )

            try:
                job = ProductionService.create_job(
                    order=data.get("order"),
                    product=data.get("product"),
                    job_type=data.get(
                        "job_type",
                        "RESTOCK",
                    ),
                    quantity_to_produce=data.get(
                        "quantity_to_produce",
                        1,
                    ),
                    assigned_to=data.get(
                        "assigned_to"
                    ),
                    created_by=employee,
                    description=data.get(
                        "description",
                        "",
                    ),
                    expected_end_date=data.get(
                        "expected_end_date"
                    ),
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    _validation_message(error),
                )

            else:
                messages.success(
                    request,
                    (
                        "Production job created "
                        "successfully."
                    ),
                )

                return redirect(
                    "furniture:production_job_detail",
                    pk=job.pk,
                )

    else:
        form = ProductionJobForm(
            initial=initial
        )

    return render(
        request,
        "furniture/production_job_form.html",
        {
            "form": form,
            "page_title": "Create Production Job",
        },
    )

# =====================================================
# QUOTATIONS
# =====================================================


@login_required
def create_quotation(request, pk):
    production_job = get_object_or_404(ProductionJob, pk=pk)
    quotation, _ = Quotation.objects.get_or_create(
        production_job=production_job,
        defaults={"prepared_by": _employee_for_user(request.user)},
    )

    form = QuotationForm(request.POST or None, instance=quotation)

    if request.method == "POST" and form.is_valid():
        quotation = form.save(commit=False)
        quotation.production_job = production_job
        quotation.prepared_by = (
            quotation.prepared_by or _employee_for_user(request.user)
        )
        quotation.status = "DRAFT"
        quotation.save()

        try:
            QuotationService.submit(quotation, user=request.user)
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Quotation submitted successfully.")
            return redirect("furniture:quotation_list")

    return render(
        request,
        "furniture/quotation_form.html",
        {"form": form, "production_job": production_job},
    )


@login_required
def quotation_list(request):
    quotations = Quotation.objects.select_related(
        "production_job",
        "prepared_by",
        "approved_by",
    ).order_by("-created_at")

    status = request.GET.get("status", "SUBMITTED").upper()
    if status != "ALL":
        quotations = quotations.filter(status=status)

    return render(
        request,
        "furniture/quotation_list.html",
        {
            "quotations": quotations,
            "selected_status": status,
            "status_choices": Quotation.STATUS,
        },
    )

@login_required
def approve_quotation(request, pk):
    quotation = get_object_or_404(
        Quotation.objects.select_related(
            "production_job",
            "prepared_by__user",
            "approved_by__user",
        ),
        pk=pk,
    )

    if request.method == "POST":
        action = request.POST.get(
            "action"
        )

        try:
            if action == "approve":
                QuotationService.approve(
                    quotation=quotation,
                    approved_by=request.user,
                )

                messages.success(
                    request,
                    "Quotation approved successfully.",
                )

            elif action == "reject":
                QuotationService.reject(
                    quotation=quotation,
                    rejected_by=request.user,
                    reason=request.POST.get(
                        "reason",
                        "",
                    ),
                )

                messages.warning(
                    request,
                    "Quotation rejected.",
                )

            else:
                messages.error(
                    request,
                    "Invalid quotation action.",
                )

        except ValidationError as error:
            messages.error(
                request,
                "; ".join(error.messages),
            )

        return redirect(
            "furniture:quotation_list"
        )

    return render(
        request,
        "furniture/approve_quotation.html",
        {
            "quotation": quotation,
        },
    )


# =====================================================
# PRODUCTION RESOURCES
# =====================================================
@login_required
def add_material(request, pk):
    production_job = get_object_or_404(
        ProductionJob,
        pk=pk,
    )

    if request.method == "POST":
        form = ProductionMaterialForm(
            request.POST
        )

        if form.is_valid():
            material = form.save(
                commit=False
            )

            material.production_job = production_job

            if not material.unit_cost:
                material.unit_cost = (
                    material.raw_material.unit_cost
                )

            material.save()

            messages.success(
                request,
                "Material usage added successfully.",
            )

            return redirect(
                "furniture:production_job_detail",
                pk=production_job.pk,
            )

    else:
        form = ProductionMaterialForm()

    return render(
        request,
        "furniture/material_form.html",
        {
            "form": form,
            "production_job": production_job,
        },
    )


@login_required
def add_labour(request, pk):
    production_job = get_object_or_404(ProductionJob, pk=pk)
    form = ProductionLabourForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        labour = form.save(commit=False)
        labour.production_job = production_job
        labour.save()
        messages.success(request, "Labour usage added successfully.")
        return redirect("furniture:production_job_detail", pk=pk)

    return render(
        request,
        "furniture/labour_form.html",
        {"form": form, "production_job": production_job},
    )


@login_required
def add_machine(request, pk):
    production_job = get_object_or_404(ProductionJob, pk=pk)
    form = ProductionMachineForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        machine = form.save(commit=False)
        machine.production_job = production_job
        machine.save()
        messages.success(request, "Machine usage added successfully.")
        return redirect("furniture:production_job_detail", pk=pk)

    return render(
        request,
        "furniture/machine_form.html",
        {"form": form, "production_job": production_job},
    )


@login_required
def add_output(request, pk):
    production_job = get_object_or_404(
        ProductionJob,
        pk=pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = ProductionOutputForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            output = form.save(
                commit=False
            )

            output.production_job = (
                production_job
            )

            if employee:
                output.produced_by = employee

            output.save()

            messages.success(
                request,
                "Production output recorded successfully.",
            )

            return redirect(
                "furniture:production_job_detail",
                pk=production_job.pk,
            )

    else:
        form = ProductionOutputForm(
            initial={
                "product": production_job.product,
            }
        )

    return render(
        request,
        "furniture/output_form.html",
        {
            "form": form,
            "production_job": production_job,
            "page_title": "Record Production Output",
        },
    )


@login_required
def material_list(request):
    materials = (
        ProductionMaterial.objects
        .select_related(
            "production_job",
            "production_job__product",
            "raw_material",
        )
        .order_by("-id")
    )

    total_quantity = sum(
        (
            material.quantity_used
            or Decimal("0.00")
        )
        for material in materials
    )

    total_cost = sum(
        (
            material.total_cost
            or Decimal("0.00")
        )
        for material in materials
    )

    return render(
        request,
        "furniture/material_list.html",
        {
            "materials": materials,
            "total_quantity": total_quantity,
            "total_cost": total_cost,
        },
    )

@login_required
def labour_list(request):
    labours = (
        ProductionLabour.objects
        .select_related(
            "production_job",
            "production_job__product",
            "employee",
        )
        .order_by("-id")
    )

    total_hours = sum(
        labour.hours_worked or Decimal("0.00")
        for labour in labours
    )

    total_cost = sum(
        labour.total_cost or Decimal("0.00")
        for labour in labours
    )

    unique_workers = (
        labours
        .exclude(employee__isnull=True)
        .values("employee_id")
        .distinct()
        .count()
    )

    return render(
        request,
        "furniture/labour_list.html",
        {
            "labours": labours,
            "total_hours": total_hours,
            "total_cost": total_cost,
            "unique_workers": unique_workers,
        },
    )



@login_required
def machine_list(request):
    machines = (
        ProductionMachine.objects
        .select_related(
            "production_job",
            "production_job__product",
            "asset",
        )
        .order_by("-id")
    )

    total_hours = sum(
        machine.hours_used or Decimal("0.00")
        for machine in machines
    )

    total_cost = sum(
        machine.total_cost or Decimal("0.00")
        for machine in machines
    )

    unique_machines = (
        machines
        .values("asset_id")
        .distinct()
        .count()
    )

    return render(
        request,
        "furniture/machine_list.html",
        {
            "machines": machines,
            "total_hours": total_hours,
            "total_cost": total_cost,
            "unique_machines": unique_machines,
        },
    )


@login_required
def output_list(request):
    outputs = (
        ProductionOutput.objects
        .select_related(
            "production_job",
            "production_job__product",
            "legacy_order",
            "product",
            "produced_by",
        )
        .order_by("-produced_at")
    )

    total_quantity = sum(
        Decimal(
            str(output.quantity_produced or 0)
        )
        for output in outputs
    )

    total_production_cost = sum(
        (
            output.total_cost
            or Decimal("0.00")
        )
        for output in outputs
    )

    average_cost_per_unit = Decimal("0.00")

    if total_quantity > 0:
        average_cost_per_unit = (
            total_production_cost
            / total_quantity
        ).quantize(
            Decimal("0.01")
        )

    production_jobs_count = (
        outputs
        .exclude(production_job__isnull=True)
        .values("production_job_id")
        .distinct()
        .count()
    )

    return render(
        request,
        "furniture/output_list.html",
        {
            "outputs": outputs,
            "total_quantity": total_quantity,
            "total_production_cost": (
                total_production_cost
            ),
            "average_cost_per_unit": (
                average_cost_per_unit
            ),
            "production_jobs_count": (
                production_jobs_count
            ),
        },
    )

# =====================================================
# PRODUCTION TASKS
# =====================================================


@login_required
def production_task_list(request):
    tasks = ProductionTask.objects.select_related(
        "production_job",
        "assigned_to",
        "created_by",
    ).order_by("production_job", "sequence")

    status = request.GET.get("status")
    employee_id = request.GET.get("employee")
    job_id = request.GET.get("job")

    if status:
        tasks = tasks.filter(status=status.upper())
    if employee_id:
        tasks = tasks.filter(assigned_to_id=employee_id)
    if job_id:
        tasks = tasks.filter(production_job_id=job_id)

    return render(
        request,
        "furniture/production_task_list.html",
        {
            "tasks": tasks,
            "status_choices": ProductionTask.STATUS,
            "selected_status": status or "",
        },
    )


@login_required
def my_production_tasks(request):
    employee = _employee_for_user(request.user)
    tasks = ProductionTask.objects.none()

    if employee:
        tasks = ProductionTask.objects.filter(
            assigned_to=employee,
        ).select_related("production_job").order_by(
            "status",
            "planned_end",
            "sequence",
        )

    return render(
        request,
        "furniture/my_production_tasks.html",
        {"tasks": tasks, "employee": employee},
    )


@login_required
def production_task_detail(request, pk):
    task = get_object_or_404(
        ProductionTask.objects.select_related(
            "production_job",
            "assigned_to",
            "created_by",
        ).prefetch_related(
            "assignments__employee",
            "logs__employee",
            "checklist_items__completed_by",
            "progress_updates__employee",
            "machine_usage_logs__machine",
        ),
        pk=pk,
    )

    return render(
        request,
        "furniture/production_task_detail.html",
        {"task": task},
    )


@login_required
def production_task_create(request):
    job_id = request.GET.get("job") or request.POST.get("production_job")
    production_job = None

    if job_id:
        production_job = get_object_or_404(ProductionJob, pk=job_id)

    form = ProductionTaskForm(
        request.POST or None,
        production_job=production_job,
    )

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        employee = _employee_for_user(request.user)

        try:
            task = ProductionTaskService.create_task(
                production_job=data["production_job"],
                name=data["name"],
                task_type=data.get("task_type", "OTHER"),
                description=data.get("description", ""),
                sequence=data.get("sequence", 1),
                priority=data.get("priority", "NORMAL"),
                assigned_to=data.get("assigned_to"),
                planned_hours=data.get("planned_hours") or Decimal("0.00"),
                planned_start=data.get("planned_start"),
                planned_end=data.get("planned_end"),
                created_by=employee,
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Production task created successfully.")
            return redirect("furniture:production_task_detail", pk=task.pk)

    return render(
        request,
        "furniture/production_task_form.html",
        {"form": form, "production_job": production_job},
    )


@login_required
def production_task_update(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionTaskForm(request.POST or None, instance=task)

    if request.method == "POST" and form.is_valid():
        task = form.save()
        messages.success(request, "Production task updated successfully.")
        return redirect("furniture:production_task_detail", pk=task.pk)

    return render(
        request,
        "furniture/production_task_form.html",
        {"form": form, "task": task},
    )


@login_required
def production_task_delete(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)

    if request.method == "POST":
        try:
            ProductionTaskService.cancel_task(
                task=task,
                employee=_employee_for_user(request.user),
                reason=request.POST.get("reason", "Cancelled by user."),
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Production task cancelled successfully.")
        return redirect("furniture:production_task_list")

    return render(
        request,
        "furniture/production_task_confirm_delete.html",
        {"task": task},
    )


@login_required
def production_task_assign(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionTaskAssignmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            ProductionTaskService.assign_worker(
                task=task,
                employee=form.cleaned_data["employee"],
                assigned_by=_employee_for_user(request.user),
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Task assigned successfully.")
            return redirect("furniture:production_task_detail", pk=task.pk)

    return render(
        request,
        "furniture/production_task_assign.html",
        {"task": task, "form": form},
    )


@login_required
@require_POST
def production_task_start(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    try:
        ProductionTaskService.start_task(
            task=task,
            employee=_employee_for_user(request.user),
            note=request.POST.get("note", ""),
        )
        messages.success(request, "Task started successfully.")
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    return redirect("furniture:production_task_detail", pk=pk)


@login_required
@require_POST
def production_task_resume(request, pk):
    return production_task_start(request, pk)


@login_required
def production_task_pause(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionTaskActionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            ProductionTaskService.pause_task(
                task=task,
                employee=_employee_for_user(request.user),
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Task paused successfully.")
            return redirect("furniture:production_task_detail", pk=pk)

    return render(
        request,
        "furniture/production_task_action.html",
        {"task": task, "form": form, "action_title": "Pause Task"},
    )


@login_required
def production_task_block(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionTaskBlockForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            ProductionTaskService.block_task(
                task=task,
                employee=_employee_for_user(request.user),
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.warning(request, "Task blocked.")
            return redirect("furniture:production_task_detail", pk=pk)

    return render(
        request,
        "furniture/production_task_action.html",
        {"task": task, "form": form, "action_title": "Block Task"},
    )


@login_required
def production_task_cancel(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionTaskActionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            ProductionTaskService.cancel_task(
                task=task,
                employee=_employee_for_user(request.user),
                reason=form.cleaned_data.get("note", ""),
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Task cancelled successfully.")
            return redirect("furniture:production_task_detail", pk=pk)

    return render(
        request,
        "furniture/production_task_action.html",
        {"task": task, "form": form, "action_title": "Cancel Task"},
    )


@login_required
def production_task_complete(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionTaskActionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            ProductionTaskService.complete_task(
                task=task,
                employee=_employee_for_user(request.user),
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Task completed successfully.")
            return redirect("furniture:production_task_detail", pk=pk)

    return render(
        request,
        "furniture/production_task_action.html",
        {"task": task, "form": form, "action_title": "Complete Task"},
    )


@login_required
def production_task_progress(request, pk):
    task = get_object_or_404(
        ProductionTask.objects.select_related(
            "production_job",
            "assigned_to",
        ).prefetch_related("progress_updates__employee"),
        pk=pk,
    )
    form = ProductionTaskProgressForm(
        request.POST or None,
        request.FILES or None,
        task=task,
    )

    if request.method == "POST" and form.is_valid():
        try:
            ProductionTaskService.update_progress(
                task=task,
                progress_percentage=form.cleaned_data["progress_percentage"],
                employee=_employee_for_user(request.user),
                hours_worked=(
                    form.cleaned_data.get("hours_worked")
                    or Decimal("0.00")
                ),
                image=form.cleaned_data.get("image"),
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, "Task progress updated successfully.")
            return redirect("furniture:production_task_detail", pk=task.pk)

    return render(
        request,
        "furniture/production_task_progress.html",
        {"task": task, "form": form},
    )


@login_required
def production_task_checklist(request, pk):
    task = get_object_or_404(ProductionTask, pk=pk)
    form = ProductionChecklistForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.task = task
        item.save()
        messages.success(request, "Checklist item added successfully.")
        return redirect("furniture:production_task_detail", pk=task.pk)

    return render(
        request,
        "furniture/production_task_checklist.html",
        {"task": task, "form": form},
    )


@login_required
@require_POST
def production_checklist_toggle(request, pk):
    item = get_object_or_404(
        ProductionChecklist.objects.select_related("task"),
        pk=pk,
    )
    employee = _employee_for_user(request.user)

    if item.is_completed:
        item.is_completed = False
        item.completed_by = None
        item.completed_at = None
        item.save(
            update_fields=["is_completed", "completed_by", "completed_at"]
        )
    else:
        item.mark_completed(employee)

    return redirect("furniture:production_task_detail", pk=item.task_id)


# =====================================================
# PRODUCTION JOB KANBAN MOVE
# =====================================================


@login_required
@require_POST
@transaction.atomic
def kanban_move_job(request, pk):
    production_job = get_object_or_404(
        ProductionJob.objects.select_for_update(),
        pk=pk,
    )

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "message": "Invalid JSON request."},
            status=400,
        )

    target_status = str(payload.get("status", "")).strip().upper()
    note = str(payload.get("note", "")).strip()

    valid_statuses = {code for code, _label in ProductionJob.STATUS}
    if not target_status or target_status not in valid_statuses:
        return JsonResponse(
            {"success": False, "message": "Invalid target production status."},
            status=400,
        )

    current_status = production_job.status

    if current_status == target_status:
        return JsonResponse(
            {
                "success": True,
                "message": "Production job is already in this stage.",
                "job_id": production_job.pk,
                "status": current_status,
            }
        )

    if current_status in {"DELIVERED", "CANCELLED"}:
        return JsonResponse(
            {
                "success": False,
                "message": "Delivered or cancelled jobs cannot be moved.",
            },
            status=400,
        )

    try:
        next_step = WorkflowRegistry.get_next_step(
            "FURNITURE_PRODUCTION",
            current_status,
        )

        if next_step is None:
            raise ValidationError(
                f"No next workflow stage exists after {current_status}."
            )

        if next_step.code != target_status:
            raise ValidationError(
                f"Invalid transition: {current_status} -> {target_status}. "
                f"Allowed next stage: {next_step.code}."
            )

        if next_step.requires_approval:
            return JsonResponse(
                {
                    "success": False,
                    "requires_approval": True,
                    "message": (
                        f"Transition to {target_status} requires approval."
                    ),
                },
                status=403,
            )

        WorkflowService.move(
            obj=production_job,
            workflow_code="FURNITURE_PRODUCTION",
            to_step=target_status,
            user=request.user,
            note=note or "Moved from Furniture Kanban board",
        )

        production_job.refresh_from_db()

        ProductionTimeline.objects.create(
            production_job=production_job,
            action="Kanban stage changed",
            from_status=current_status,
            to_status=production_job.status,
            performed_by=_employee_for_user(request.user),
            note=note or "Moved from Furniture Kanban board",
        )

    except ValidationError as error:
        return JsonResponse(
            {"success": False, "message": _validation_message(error)},
            status=400,
        )
    except Exception as error:
        return JsonResponse(
            {"success": False, "message": str(error)},
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
            "message": (
                f"Production job #{production_job.pk} moved from "
                f"{current_status} to {production_job.status}."
            ),
            "job_id": production_job.pk,
            "previous_status": current_status,
            "status": production_job.status,
            "status_label": production_job.get_status_display(),
        }
    )


# =====================================================
# REPORTS
# =====================================================


@login_required
def production_reports(request):
    jobs = ProductionJob.objects.select_related("product", "order")
    quotations = Quotation.objects.select_related("production_job")

    total_cost = sum(
        (quotation.total_cost for quotation in quotations),
        Decimal("0.00"),
    )
    total_selling_price = sum(
        (quotation.expected_selling_price for quotation in quotations),
        Decimal("0.00"),
    )

    return render(
        request,
        "furniture/production_reports.html",
        {
            "jobs": jobs,
            "quotations": quotations,
            "total_cost": total_cost,
            "total_selling_price": total_selling_price,
            "expected_profit": total_selling_price - total_cost,
        },
    )

@login_required
def production_job_cost_report(request, pk):
    job = get_object_or_404(
        ProductionJob,
        pk=pk,
    )

    settings_object = ProductionSettings.get_settings()

    cost_summary = ProductionCostService.job_cost_summary(
        production_job=job,
        overhead_rate=settings_object.overhead_rate,
        wastage_rate=settings_object.wastage_rate,
        transport_cost=settings_object.default_transport_cost,
        other_cost=settings_object.default_other_cost,
    )

    return render(
        request,
        "furniture/production_job_cost_report.html",
        {
            "job": job,
            "cost": cost_summary,
            "production_settings": settings_object,
        },
    )
@login_required
def production_settings(request):
    settings_object = ProductionSettings.get_settings()

    if request.method == "POST":
        form = ProductionSettingsForm(
            request.POST,
            instance=settings_object,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Furniture production settings updated successfully.",
            )

            return redirect(
                "furniture:production_settings"
            )
    else:
        form = ProductionSettingsForm(
            instance=settings_object
        )

    return render(
        request,
        "furniture/production_settings.html",
        {
            "form": form,
            "settings_object": settings_object,
        },
    )


# =====================================================
# QUALITY INSPECTIONS
# =====================================================

@login_required
def quality_inspection_list(request):
    inspections = (
        QualityInspection.objects
        .select_related(
            "production_job",
            "production_job__product",
            "inspector",
            "approved_by",
        )
        .prefetch_related("defects")
        .order_by("-inspected_at")
    )

    result_filter = request.GET.get("result", "").strip()
    inspection_type = request.GET.get(
        "inspection_type",
        "",
    ).strip()
    query = request.GET.get("q", "").strip()

    if result_filter:
        inspections = inspections.filter(
            result=result_filter
        )

    if inspection_type:
        inspections = inspections.filter(
            inspection_type=inspection_type
        )

    if query:
        inspections = inspections.filter(
            Q(production_job__description__icontains=query)
            | Q(production_job__product__name__icontains=query)
            | Q(remarks__icontains=query)
        )

    summary = {
        "total": inspections.count(),
        "pending": inspections.filter(
            result="PENDING"
        ).count(),
        "passed": inspections.filter(
            result="PASSED"
        ).count(),
        "failed": inspections.filter(
            result="FAILED"
        ).count(),
        "conditional": inspections.filter(
            result="CONDITIONAL"
        ).count(),
    }

    return render(
        request,
        "furniture/quality/inspection_list.html",
        {
            "inspections": inspections,
            "summary": summary,
            "result_filter": result_filter,
            "inspection_type_filter": inspection_type,
            "query": query,
        },
    )

@login_required
def quality_inspection_detail(request, pk):
    inspection = get_object_or_404(
        QualityInspection.objects.select_related(
            "production_job",
            "production_job__product",
            "inspector",
            "approved_by",
        ).prefetch_related(
            "defects__reported_by",
            "defects__resolved_by",
            "defects__rework_orders__assigned_to",
        ),
        pk=pk,
    )

    quality_summary = QualityService.job_quality_summary(
        inspection.production_job
    )

    return render(
        request,
        "furniture/quality/inspection_detail.html",
        {
            "inspection": inspection,
            "job": inspection.production_job,
            "quality_summary": quality_summary,
        },
    )


@login_required
def quality_inspection_create(request, job_pk=None):
    production_job = None

    if job_pk is not None:
        production_job = get_object_or_404(
            ProductionJob,
            pk=job_pk,
        )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = QualityInspectionForm(
            request.POST,
            request.FILES,
            production_job=production_job,
        )

        if form.is_valid():
            try:
                inspection = QualityService.create_inspection(
                    production_job=form.cleaned_data[
                        "production_job"
                    ],
                    inspector=(
                        form.cleaned_data.get("inspector")
                        or employee
                    ),
                    inspection_type=form.cleaned_data[
                        "inspection_type"
                    ],
                    quantity_inspected=form.cleaned_data[
                        "quantity_inspected"
                    ],
                    remarks=form.cleaned_data.get(
                        "remarks",
                        "",
                    ),
                    evidence_image=form.cleaned_data.get(
                        "evidence_image"
                    ),
                )

                messages.success(
                    request,
                    "Quality inspection created successfully.",
                )

                return redirect(
                    "furniture:quality_inspection_detail",
                    pk=inspection.pk,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.messages,
                )
    else:
        form = QualityInspectionForm(
            production_job=production_job,
            initial={
                "inspector": employee,
            },
        )

    return render(
        request,
        "furniture/quality/inspection_form.html",
        {
            "form": form,
            "production_job": production_job,
            "page_title": "Create Quality Inspection",
        },
    )

@login_required
def quality_inspection_result(request, pk):
    inspection = get_object_or_404(
        QualityInspection.objects.select_related(
            "production_job",
            "inspector",
        ),
        pk=pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = QualityInspectionResultForm(
            request.POST,
            request.FILES,
            instance=inspection,
        )

        if form.is_valid():
            try:
                inspection = QualityService.record_result(
                    inspection=inspection,
                    result=form.cleaned_data["result"],
                    score=form.cleaned_data["score"],
                    quantity_inspected=(
                        form.cleaned_data[
                            "quantity_inspected"
                        ]
                    ),
                    quantity_passed=(
                        form.cleaned_data[
                            "quantity_passed"
                        ]
                    ),
                    quantity_failed=(
                        form.cleaned_data[
                            "quantity_failed"
                        ]
                    ),
                    inspector=(
                        form.cleaned_data.get("inspector")
                        or employee
                    ),
                    remarks=form.cleaned_data.get(
                        "remarks",
                        "",
                    ),
                    evidence_image=form.cleaned_data.get(
                        "evidence_image"
                    ),
                )

                messages.success(
                    request,
                    "Inspection result recorded successfully.",
                )

                return redirect(
                    "furniture:quality_inspection_detail",
                    pk=inspection.pk,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.messages,
                )
    else:
        form = QualityInspectionResultForm(
            instance=inspection,
        )

    return render(
        request,
        "furniture/quality/inspection_result_form.html",
        {
            "inspection": inspection,
            "form": form,
        },
    )

@login_required
def production_defect_create(request, inspection_pk):
    inspection = get_object_or_404(
        QualityInspection.objects.select_related(
            "production_job",
        ),
        pk=inspection_pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = ProductionDefectForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            try:
                defect = QualityService.create_defect(
                    inspection=inspection,
                    defect_type=form.cleaned_data[
                        "defect_type"
                    ],
                    severity=form.cleaned_data[
                        "severity"
                    ],
                    description=form.cleaned_data[
                        "description"
                    ],
                    affected_quantity=(
                        form.cleaned_data[
                            "affected_quantity"
                        ]
                    ),
                    root_cause=form.cleaned_data.get(
                        "root_cause",
                        "",
                    ),
                    corrective_action=(
                        form.cleaned_data.get(
                            "corrective_action",
                            "",
                        )
                    ),
                    evidence_image=form.cleaned_data.get(
                        "evidence_image"
                    ),
                    reported_by=employee,
                    rework_required=(
                        form.cleaned_data.get(
                            "rework_required",
                            True,
                        )
                    ),
                )

                messages.success(
                    request,
                    "Quality defect recorded successfully.",
                )

                return redirect(
                    "furniture:production_defect_detail",
                    pk=defect.pk,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.messages,
                )
    else:
        form = ProductionDefectForm()

    return render(
        request,
        "furniture/quality/defect_form.html",
        {
            "form": form,
            "inspection": inspection,
            "job": inspection.production_job,
        },
    )

@login_required
def production_defect_list(request):
    defects = (
        ProductionDefect.objects
        .select_related(
            "production_job",
            "production_job__product",
            "inspection",
            "reported_by",
            "resolved_by",
        )
        .order_by("-created_at")
    )

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()
    severity_filter = request.GET.get(
        "severity",
        "",
    ).strip()

    if status_filter:
        defects = defects.filter(
            status=status_filter
        )

    if severity_filter:
        defects = defects.filter(
            severity=severity_filter
        )

    return render(
        request,
        "furniture/quality/defect_list.html",
        {
            "defects": defects,
            "status_filter": status_filter,
            "severity_filter": severity_filter,
        },
    )


@login_required
def production_defect_detail(request, pk):
    defect = get_object_or_404(
        ProductionDefect.objects.select_related(
            "production_job",
            "inspection",
            "reported_by",
            "resolved_by",
        ).prefetch_related(
            "rework_orders__assigned_to",
            "rework_orders__created_by",
            "rework_orders__completed_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "furniture/quality/defect_detail.html",
        {
            "defect": defect,
            "job": defect.production_job,
        },
    )


@login_required
def rework_order_create(request, defect_pk):
    defect = get_object_or_404(
        ProductionDefect.objects.select_related(
            "production_job",
        ),
        pk=defect_pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = ReworkOrderForm(
            request.POST
        )

        if form.is_valid():
            try:
                rework = QualityService.assign_rework(
                    defect=defect,
                    assigned_to=form.cleaned_data[
                        "assigned_to"
                    ],
                    instructions=form.cleaned_data[
                        "instructions"
                    ],
                    estimated_hours=(
                        form.cleaned_data[
                            "estimated_hours"
                        ]
                        or Decimal("0.00")
                    ),
                    created_by=employee,
                )

                messages.success(
                    request,
                    "Rework order assigned successfully.",
                )

                return redirect(
                    "furniture:rework_order_detail",
                    pk=rework.pk,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.messages,
                )
    else:
        form = ReworkOrderForm()

    return render(
        request,
        "furniture/quality/rework_form.html",
        {
            "form": form,
            "defect": defect,
            "job": defect.production_job,
        },
    )

@login_required
def rework_order_list(request):
    reworks = (
        ReworkOrder.objects
        .select_related(
            "production_job",
            "defect",
            "assigned_to",
            "created_by",
            "completed_by",
        )
        .order_by("-created_at")
    )

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    if status_filter:
        reworks = reworks.filter(
            status=status_filter
        )

    return render(
        request,
        "furniture/quality/rework_list.html",
        {
            "reworks": reworks,
            "status_filter": status_filter,
        },
    )


@login_required
def rework_order_detail(request, pk):
    rework = get_object_or_404(
        ReworkOrder.objects.select_related(
            "production_job",
            "defect",
            "assigned_to",
            "created_by",
            "completed_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "furniture/quality/rework_detail.html",
        {
            "rework": rework,
            "job": rework.production_job,
        },
    )

@login_required
@require_POST
def rework_order_start(request, pk):
    rework = get_object_or_404(
        ReworkOrder,
        pk=pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    try:
        QualityService.start_rework(
            rework=rework,
            performed_by=employee,
            note=request.POST.get(
                "note",
                "",
            ),
        )

        messages.success(
            request,
            "Rework started successfully.",
        )

    except ValidationError as error:
        messages.error(
            request,
            "; ".join(error.messages),
        )

    return redirect(
        "furniture:rework_order_detail",
        pk=rework.pk,
    )

@login_required
def rework_order_complete(request, pk):
    rework = get_object_or_404(
        ReworkOrder,
        pk=pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = ReworkCompletionForm(
            request.POST,
            request.FILES,
            instance=rework,
        )

        if form.is_valid():
            try:
                QualityService.complete_rework(
                    rework=rework,
                    completed_by=employee,
                    actual_hours=(
                        form.cleaned_data[
                            "actual_hours"
                        ]
                        or Decimal("0.00")
                    ),
                    rework_cost=(
                        form.cleaned_data[
                            "rework_cost"
                        ]
                        or Decimal("0.00")
                    ),
                    completion_note=(
                        form.cleaned_data.get(
                            "completion_note",
                            "",
                        )
                    ),
                    completion_image=(
                        form.cleaned_data.get(
                            "completion_image"
                        )
                    ),
                )

                messages.success(
                    request,
                    "Rework completed successfully.",
                )

                return redirect(
                    "furniture:rework_order_detail",
                    pk=rework.pk,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.messages,
                )
    else:
        form = ReworkCompletionForm(
            instance=rework,
        )

    return render(
        request,
        "furniture/quality/rework_complete_form.html",
        {
            "rework": rework,
            "form": form,
        },
    )

@login_required
def rework_order_verify(request, pk):
    rework = get_object_or_404(
        ReworkOrder,
        pk=pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if request.method == "POST":
        form = ReworkVerificationForm(
            request.POST
        )

        if form.is_valid():
            try:
                QualityService.verify_rework(
                    rework=rework,
                    verified_by=employee,
                    passed=form.cleaned_data[
                        "passed"
                    ],
                    note=form.cleaned_data.get(
                        "note",
                        "",
                    ),
                )

                if form.cleaned_data["passed"]:
                    messages.success(
                        request,
                        "Rework verified successfully.",
                    )
                else:
                    messages.warning(
                        request,
                        "Rework failed verification and was returned.",
                    )

                return redirect(
                    "furniture:rework_order_detail",
                    pk=rework.pk,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    error.messages,
                )
    else:
        form = ReworkVerificationForm()

    return render(
        request,
        "furniture/quality/rework_verify_form.html",
        {
            "rework": rework,
            "form": form,
        },
    )

@login_required
@require_POST
def quality_inspection_approve(request, pk):
    inspection = get_object_or_404(
        QualityInspection,
        pk=pk,
    )

    employee = getattr(
        request.user,
        "employee",
        None,
    )

    if employee is None:
        messages.error(
            request,
            "Your account is not linked to an employee record.",
        )

        return redirect(
            "furniture:quality_inspection_detail",
            pk=inspection.pk,
        )

    try:
        QualityService.approve_finished_goods(
            inspection=inspection,
            approved_by=employee,
            note=request.POST.get(
                "note",
                "",
            ),
        )

        messages.success(
            request,
            "Finished goods approved successfully.",
        )

    except ValidationError as error:
        messages.error(
            request,
            "; ".join(error.messages),
        )

    return redirect(
        "furniture:quality_inspection_detail",
        pk=inspection.pk,
    )
@login_required
@require_POST
def production_schedule(request, pk):
    job = get_object_or_404(
        ProductionJob,
        pk=pk,
    )
    PlanningService.schedule_job(job)
    messages.success(
        request,
        "Production schedule generated successfully.",
    )
    return redirect(
        "furniture:production_job_detail",
        pk=job.pk,
    )


