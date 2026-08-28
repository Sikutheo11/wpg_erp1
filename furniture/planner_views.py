from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.permissions import wpg_permission_required

from .commercial_forms import ProductionPlanQuotationForm
from .planner_forms import (
    ProductionPlanAdditionalCostForm, ProductionPlanForm,
    ProductionPlanLabourForm, ProductionPlanMachineForm,
    ProductionPlanMaterialForm, ProductionPlanLabourCatalogForm,
    ProductionPlanMachineCatalogForm,
)
from .planner_models import ProductionPlan
from .services.commercial_service import CustomFurnitureQuotationService
from .services.estimation_service import ProductionPlanningCostService


def _error_text(exc):
    return "; ".join(getattr(exc, "messages", []) or [str(exc)])


@login_required
@wpg_permission_required("furniture.view_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_list(request):
    plans = (
        ProductionPlan.objects
        .select_related("order", "product", "prepared_by", "sales_quotation_item__quotation")
        .order_by("-created_at")
    )
    return render(request, "furniture/planner/plan_list.html", {"plans": plans})


@login_required
@wpg_permission_required("furniture.add_productionplan", feature_code="FURNITURE_OPERATIONS")
def order_technical_costing(request, order_id):
    from orders.models import Order

    order = get_object_or_404(Order, pk=order_id, business_unit="FURNITURE")

    existing = (
        ProductionPlan.objects.filter(order=order)
        .exclude(status="SUPERSEDED")
        .order_by("-created_at")
        .first()
    )
    if existing:
        return redirect("furniture:planner_detail", pk=existing.pk)

    plan = ProductionPlan.objects.create(
        order=order,
        name=f"Technical Costing - {order.order_number}",
        quantity=1,
    )
    try:
        plan.prepared_by = request.user.employee
        plan.save(update_fields=["prepared_by"])
    except (AttributeError, ObjectDoesNotExist):
        pass

    ProductionPlanningCostService.initialise_plan_defaults(plan)
    messages.info(
        request,
        "Technical costing plan created. Add raw materials, labour, machines and other costs.",
    )
    return redirect("furniture:planner_detail", pk=plan.pk)


@login_required
@wpg_permission_required("furniture.add_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_create(request):
    form = ProductionPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        try:
            plan.prepared_by = request.user.employee
        except (AttributeError, ObjectDoesNotExist):
            plan.prepared_by = None
        plan.save()
        ProductionPlanningCostService.initialise_plan_defaults(plan)
        messages.success(request, "Production plan created.")
        return redirect("furniture:planner_detail", pk=plan.pk)
    return render(request, "furniture/planner/plan_form.html", {"form": form, "title": "New Production Plan"})


@login_required
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_edit(request, pk):
    plan = get_object_or_404(ProductionPlan, pk=pk)
    form = ProductionPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Production plan updated.")
        return redirect("furniture:planner_detail", pk=plan.pk)
    return render(request, "furniture/planner/plan_form.html", {"form": form, "plan": plan, "title": "Edit Production Plan"})


@login_required
@wpg_permission_required("furniture.view_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_detail(request, pk):
    plan = get_object_or_404(
        ProductionPlan.objects.select_related(
            "order", "product", "prepared_by", "reviewed_by",
            "sales_quotation_item__quotation",
        ),
        pk=pk,
    )
    quotation = plan.order.customer_quotation if plan.order_id else None
    context = {
        "plan": plan,
        "quotation": quotation,
        "material_form": ProductionPlanMaterialForm(),
        "labour_form": ProductionPlanLabourCatalogForm(),
        "machine_form": ProductionPlanMachineCatalogForm(),
        "additional_form": ProductionPlanAdditionalCostForm(),
        "quotation_form": ProductionPlanQuotationForm(
            initial={
                "discount": getattr(quotation, "discount", 0),
                "tax": getattr(quotation, "tax", 0),
                "notes": getattr(quotation, "notes", ""),
                "valid_until": getattr(quotation, "valid_until", None),
            }
        ),
    }
    return render(request, "furniture/planner/plan_detail.html", context)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_import_bom(request, pk):
    plan = get_object_or_404(ProductionPlan, pk=pk)
    try:
        result = ProductionPlanningCostService.sync_from_bom(
            plan, replace=request.POST.get("replace") == "1"
        )
        messages.success(request, f"BOM imported: {result['created']} created, {result['updated']} updated.")
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect("furniture:planner_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_finish(request, pk):
    plan = get_object_or_404(ProductionPlan, pk=pk)
    try:
        ProductionPlanningCostService.calculate(plan)
        label = plan.order.order_number if plan.order_id else plan.name
        messages.success(request, f"Technical costing for {label} was saved successfully.")
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("furniture:planner_detail", pk=pk)

    return redirect("orders:all_orders")


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_calculate(request, pk):
    plan = get_object_or_404(ProductionPlan, pk=pk)
    try:
        ProductionPlanningCostService.calculate(plan)
        messages.success(request, "Estimated costing recalculated.")
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect("furniture:planner_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_generate_quotation(request, pk):
    plan = get_object_or_404(ProductionPlan.objects.select_related("order"), pk=pk)
    if not plan.order_id:
        messages.error(request, "Link this plan to a Custom Furniture order first.")
        return redirect("furniture:planner_detail", pk=pk)

    form = ProductionPlanQuotationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Correct the quotation settings and try again.")
        return redirect("furniture:planner_detail", pk=pk)

    try:
        quotation = CustomFurnitureQuotationService.sync_order_quotation(
            order=plan.order, actor=request.user, **form.cleaned_data
        )
        messages.success(
            request,
            f"Customer quotation {quotation.quotation_no} prepared from all calculated plans on this order.",
        )
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect("furniture:planner_detail", pk=pk)


def _add_line(request, pk, form_class):
    plan = get_object_or_404(ProductionPlan, pk=pk)
    form = form_class(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.plan = plan
        line.save()
        messages.success(request, "Planning line added.")
    else:
        messages.error(request, "Please correct the planning line.")
    return redirect("furniture:planner_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_add_material(request, pk):
    return _add_line(request, pk, ProductionPlanMaterialForm)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_add_labour(request, pk):
    return _add_line(request, pk, ProductionPlanLabourCatalogForm)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_add_machine(request, pk):
    return _add_line(request, pk, ProductionPlanMachineCatalogForm)


@login_required
@require_POST
@wpg_permission_required("furniture.change_productionplan", feature_code="FURNITURE_OPERATIONS")
def production_plan_add_additional(request, pk):
    return _add_line(request, pk, ProductionPlanAdditionalCostForm)
