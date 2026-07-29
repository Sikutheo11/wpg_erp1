from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .forms import (
    AgricultureOperationForm,
    DailyFlockRecordForm,
    EggProductionForm,
    FeedingRecordForm,
    HealthRecordForm,
    IncubationBatchForm,
    IncubationCandlingForm,
    IncubationCompletionForm,
    MortalityRecordForm,
    OperationNoteForm,
    OperationReasonForm,
    PoultryBreedForm,
    PoultryFarmForm,
    PoultryFlockForm,
    PoultryHouseForm,
)
from .models import (
    AgricultureOperation,
    EggProduction,
    IncubationBatch,
    MortalityRecord,
    PoultryBreed,
    PoultryFarm,
    PoultryFlock,
    PoultryHouse,
)
from .permissions import (
    agriculture_dashboard_required,
    breed_add_required,
    breed_view_required,
    daily_record_add_required,
    egg_production_add_required,
    farm_add_required,
    farm_edit_required,
    farm_view_required,
    feeding_add_required,
    flock_add_required,
    flock_view_required,
    health_add_required,
    house_add_required,
    incubation_add_required,
    incubation_edit_required,
    incubation_view_required,
    mortality_add_required,
    operation_add_required,
    operation_view_required,
    require_feeding_finance_post,
    require_health_finance_post,
    reports_view_required,
    house_edit_required,
)
from .services import (
    AgricultureFinanceIntegrationService,
    AgricultureOperationService,
    AgricultureValuationService,
    PoultryService,
)


def _validation_messages(request, error):
    if hasattr(error, "message_dict"):
        for field, field_messages in error.message_dict.items():
            label = field.replace("_", " ").title()
            for message in field_messages:
                messages.error(request, f"{label}: {message}")
        return

    for message in getattr(error, "messages", [str(error)]):
        messages.error(request, message)


def _form_service_error(form, error):
    if hasattr(error, "message_dict"):
        for field, field_messages in error.message_dict.items():
            target = field if field in form.fields else None
            for message in field_messages:
                form.add_error(target, message)
        return

    for message in getattr(error, "messages", [str(error)]):
        form.add_error(None, message)


@login_required
@agriculture_dashboard_required
def dashboard(request):
    active_flocks = PoultryFlock.objects.filter(
        status__in={"ACTIVE", "QUARANTINED"}
    )
    context = {
        "total_farms": PoultryFarm.objects.filter(is_active=True).count(),
        "active_flocks": active_flocks.count(),
        "current_birds": active_flocks.aggregate(
            total=Coalesce(Sum("current_quantity"), 0)
        )["total"],
        "pending_operations": AgricultureOperation.objects.filter(
            status="PENDING"
        ).count(),
        "active_operations": AgricultureOperation.objects.filter(
            status__in={"APPROVED", "ACTIVE", "ON_HOLD"}
        ).count(),
        "recent_operations": AgricultureOperation.objects.select_related(
            "farm",
            "assigned_to",
            "source_order",
        )[:8],
        "recent_egg_records": EggProduction.objects.select_related(
            "flock",
            "flock__farm",
        )[:8],
        "recent_mortality": MortalityRecord.objects.select_related(
            "flock",
            "flock__farm",
        )[:8],
        "incubation_summary": IncubationBatch.objects.values("status")
        .annotate(total=Count("id"))
        .order_by("status"),
    }
    return render(request, "agriculture/dashboard.html", context)


# ---------------------------------------------------------------------------
# Farms, houses and breeds
# ---------------------------------------------------------------------------


@login_required
@farm_view_required
def farm_list(request):
    farms = PoultryFarm.objects.select_related(
        "manager",
        "warehouse",
    ).annotate(
        house_count=Count("houses", distinct=True),
        flock_count=Count("flocks", distinct=True),
    )
    return render(
        request,
        "agriculture/farms/farm_list.html",
        {"farms": farms},
    )


@login_required
@farm_add_required
def farm_create(request):
    form = PoultryFarmForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        farm = form.save()
        messages.success(request, f"Farm {farm.name} created successfully.")
        return redirect("agriculture:farm_detail", pk=farm.pk)

    return render(
        request,
        "agriculture/farms/farm_form.html",
        {"form": form, "title": "Create Poultry Farm"},
    )


@login_required
@farm_edit_required
def farm_update(request, pk):
    farm = get_object_or_404(PoultryFarm, pk=pk)
    form = PoultryFarmForm(
        request.POST or None,
        instance=farm,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        farm = form.save()
        messages.success(request, f"Farm {farm.name} updated successfully.")
        return redirect("agriculture:farm_detail", pk=farm.pk)

    return render(
        request,
        "agriculture/farms/farm_form.html",
        {"form": form, "farm": farm, "title": "Update Poultry Farm"},
    )


@login_required
@farm_view_required
def farm_detail(request, pk):
    farm = get_object_or_404(
        PoultryFarm.objects.select_related("manager", "warehouse"),
        pk=pk,
    )
    context = {
        "farm": farm,
        "houses": farm.houses.all().order_by("code"),
        "flocks": farm.flocks.select_related("house", "breed").order_by(
            "-arrival_or_hatch_date"
        ),
        "operations": farm.operations.select_related(
            "assigned_to",
            "source_order",
        )[:10],
    }
    return render(request, "agriculture/farms/farm_detail.html", context)


@login_required
@house_add_required
def house_create(request, farm_pk=None):
    farm = None

    if farm_pk is not None:
        farm = get_object_or_404(
            PoultryFarm.objects.select_related("warehouse"),
            pk=farm_pk,
            is_active=True,
        )

    form = PoultryHouseForm(
        request.POST or None,
        farm=farm,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        house = form.save(commit=False)

        if farm is not None:
            house.farm = farm

        house.save()

        messages.success(
            request,
            f"House {house.code} created successfully.",
        )

        return redirect(
            "agriculture:farm_detail",
            pk=house.farm_id,
        )

    return render(
        request,
        "agriculture/houses/house_form.html",
        {
            "form": form,
            "farm": farm,
            "title": "Create Poultry House",
            "submit_label": "Save House",
        },
    )

@login_required
@house_edit_required
def house_update(request, pk):
    house = get_object_or_404(
        PoultryHouse.objects.select_related(
            "farm",
            "farm__warehouse",
        ),
        pk=pk,
    )

    form = PoultryHouseForm(
        request.POST or None,
        instance=house,
        farm=house.farm,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        house = form.save()

        messages.success(
            request,
            f"House {house.code} updated successfully.",
        )

        return redirect(
            "agriculture:farm_detail",
            pk=house.farm_id,
        )

    return render(
        request,
        "agriculture/houses/house_form.html",
        {
            "form": form,
            "farm": house.farm,
            "house": house,
            "title": f"Edit House {house.code}",
            "submit_label": "Update House",
        },
    )

@login_required
@breed_view_required
def breed_list(request):
    breeds = PoultryBreed.objects.all()
    return render(
        request,
        "agriculture/breeds/breed_list.html",
        {"breeds": breeds},
    )


@login_required
@breed_add_required
def breed_create(request):
    form = PoultryBreedForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        breed = form.save()
        messages.success(request, f"Breed {breed.name} created successfully.")
        return redirect("agriculture:breed_list")

    return render(
        request,
        "agriculture/breeds/breed_form.html",
        {"form": form, "title": "Create Poultry Breed"},
    )


# ---------------------------------------------------------------------------
# Agriculture operations and Core workflow actions
# ---------------------------------------------------------------------------


@login_required
@operation_view_required
def operation_list(request):
    operations = AgricultureOperation.objects.select_related(
        "farm",
        "assigned_to",
        "source_order",
        "created_by",
    )

    status = request.GET.get("status", "").strip().upper()
    operation_type = request.GET.get("type", "").strip().upper()
    farm_id = request.GET.get("farm", "").strip()

    if status:
        operations = operations.filter(status=status)
    if operation_type:
        operations = operations.filter(operation_type=operation_type)
    if farm_id.isdigit():
        operations = operations.filter(farm_id=farm_id)

    context = {
        "operations": operations,
        "farms": PoultryFarm.objects.filter(is_active=True),
        "statuses": AgricultureOperation.STATUSES,
        "operation_types": AgricultureOperation.OPERATION_TYPES,
        "selected_status": status,
        "selected_type": operation_type,
        "selected_farm": farm_id,
    }
    return render(
        request,
        "agriculture/operations/operation_list.html",
        context,
    )


@login_required
@operation_add_required
def operation_create(request):
    form = AgricultureOperationForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            operation = AgricultureOperationService.create_operation(
                operation_type=data["operation_type"],
                farm=data["farm"],
                actor=request.user,
                source_order=data.get("source_order"),
                assigned_to=data.get("assigned_to"),
                planned_start_date=data.get("planned_start_date"),
                planned_end_date=data.get("planned_end_date"),
                budget=data["budget"],
                notes=data.get("notes", ""),
            )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            messages.success(
                request,
                f"Operation {operation.code} created as draft.",
            )
            return redirect(
                "agriculture:operation_detail",
                pk=operation.pk,
            )

    return render(
        request,
        "agriculture/operations/operation_form.html",
        {"form": form, "title": "Create Agriculture Operation"},
    )


@login_required
@operation_view_required
def operation_detail(request, pk):
    operation = get_object_or_404(
        AgricultureOperation.objects.select_related(
            "farm",
            "assigned_to",
            "source_order",
            "created_by",
            "approved_by",
        ).prefetch_related(
            "created_flocks",
            "daily_flock_records",
            "egg_production_records",
            "feeding_records",
            "health_records",
            "mortality_records",
            "incubation_batches",
        ),
        pk=pk,
    )

    try:
        available_actions = AgricultureOperationService.available_actions(
            operation=operation,
            actor=request.user,
        )
        workflow_history = AgricultureOperationService.history(
            operation=operation
        )
    except ValidationError as error:
        available_actions = {}
        workflow_history = []
        _validation_messages(request, error)

    context = {
        "operation": operation,
        "available_actions": available_actions,
        "workflow_history": workflow_history,
        "note_form": OperationNoteForm(),
        "reason_form": OperationReasonForm(),
    }
    return render(
        request,
        "agriculture/operations/operation_detail.html",
        context,
    )


@login_required
@operation_view_required
@require_POST
def operation_action(request, pk, action):
    operation = get_object_or_404(AgricultureOperation, pk=pk)
    note_form = OperationNoteForm(request.POST)
    reason_form = OperationReasonForm(request.POST)

    service_actions = {
        "submit": AgricultureOperationService.submit,
        "approve": AgricultureOperationService.approve,
        "return": AgricultureOperationService.return_for_correction,
        "start": AgricultureOperationService.start,
        "hold": AgricultureOperationService.hold,
        "resume": AgricultureOperationService.resume,
        "complete": AgricultureOperationService.complete,
    }

    try:
        if action == "cancel":
            if not reason_form.is_valid():
                raise ValidationError(reason_form.errors.as_text())
            updated = AgricultureOperationService.cancel(
                operation=operation,
                actor=request.user,
                reason=reason_form.cleaned_data["reason"],
            )
        else:
            service_method = service_actions.get(action)
            if service_method is None:
                raise Http404("Unknown agriculture workflow action.")
            if not note_form.is_valid():
                raise ValidationError(note_form.errors.as_text())

            updated = service_method(
                operation=operation,
                actor=request.user,
                note=note_form.cleaned_data.get("note", ""),
            )
    except ValidationError as error:
        _validation_messages(request, error)
    else:
        messages.success(
            request,
            f"Operation {updated.code} is now {updated.get_status_display()}.",
        )

    return redirect("agriculture:operation_detail", pk=operation.pk)


# ---------------------------------------------------------------------------
# Flocks and daily production records
# ---------------------------------------------------------------------------


@login_required
@flock_view_required
def flock_list(request):
    flocks = PoultryFlock.objects.select_related(
        "farm",
        "house",
        "breed",
        "source_operation",
    )
    status = request.GET.get("status", "").strip().upper()
    purpose = request.GET.get("purpose", "").strip().upper()
    farm_id = request.GET.get("farm", "").strip()

    if status:
        flocks = flocks.filter(status=status)
    if purpose:
        flocks = flocks.filter(purpose=purpose)
    if farm_id.isdigit():
        flocks = flocks.filter(farm_id=farm_id)

    context = {
        "flocks": flocks,
        "farms": PoultryFarm.objects.filter(is_active=True),
        "statuses": PoultryFlock.STATUSES,
        "purposes": PoultryFlock.PURPOSES,
        "selected_status": status,
        "selected_purpose": purpose,
        "selected_farm": farm_id,
    }
    return render(request, "agriculture/flocks/flock_list.html", context)


@login_required
@flock_add_required
def flock_create(request):
    farm = None
    farm_id = request.GET.get("farm") or request.POST.get("farm")
    if farm_id and str(farm_id).isdigit():
        farm = get_object_or_404(PoultryFarm, pk=farm_id)

    form = PoultryFlockForm(
        request.POST or None,
        user=request.user,
        farm=farm,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            flock = PoultryService.create_flock(
                farm=data["farm"],
                house=data["house"],
                breed=data["breed"],
                purpose=data["purpose"],
                source=data["source"],
                arrival_or_hatch_date=data["arrival_or_hatch_date"],
                initial_quantity=data["initial_quantity"],
                actor=request.user,
                source_operation=data.get("source_operation"),
                average_unit_cost=data["average_unit_cost"],
                livestock_product=data.get("livestock_product"),
                notes=data.get("notes", ""),
            )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            messages.success(request, f"Flock {flock.code} created.")
            return redirect("agriculture:flock_detail", pk=flock.pk)

    return render(
        request,
        "agriculture/flocks/flock_form.html",
        {"form": form, "farm": farm, "title": "Create Poultry Flock"},
    )


@login_required
@flock_view_required
def flock_detail(request, pk):
    flock = get_object_or_404(
        PoultryFlock.objects.select_related(
            "farm",
            "house",
            "breed",
            "source_operation",
            "livestock_product",
        ).prefetch_related(
            "daily_records",
            "egg_production_records",
            "feeding_records",
            "health_records",
            "mortality_records",
            "incubation_batches",
        ),
        pk=pk,
    )
    return render(
        request,
        "agriculture/flocks/flock_detail.html",
        {
            "flock": flock,
            "daily_records": flock.daily_records.all()[:15],
            "egg_records": flock.egg_production_records.all()[:15],
            "feeding_records": flock.feeding_records.all()[:15],
            "health_records": flock.health_records.all()[:15],
            "mortality_records": flock.mortality_records.all()[:15],
        },
    )


@login_required
@daily_record_add_required
def daily_record_create(request, flock_pk):
    flock = get_object_or_404(PoultryFlock, pk=flock_pk)
    form = DailyFlockRecordForm(
        request.POST or None,
        user=request.user,
        flock=flock,
    )
    if request.method == "POST":
        form.instance.flock = flock
        form.instance.opening_quantity = flock.current_quantity

        def posted_quantity(name):
            try:
                return max(int(request.POST.get(name, 0)), 0)
            except (TypeError, ValueError):
                return 0

        form.instance.closing_quantity = (
            flock.current_quantity
            + posted_quantity("additions")
            + posted_quantity("transferred_in")
            - posted_quantity("mortality")
            - posted_quantity("culls")
            - posted_quantity("sold")
            - posted_quantity("transferred_out")
        )
        if form.is_valid():
            data = form.cleaned_data
            try:
                PoultryService.record_daily_flock(
                    flock=flock,
                    actor=request.user,
                    operation=data.get("operation"),
                    record_date=data["record_date"],
                    additions=data["additions"],
                    transferred_in=data["transferred_in"],
                    mortality=data["mortality"],
                    culls=data["culls"],
                    sold=data["sold"],
                    transferred_out=data["transferred_out"],
                    average_weight_kg=data.get("average_weight_kg"),
                    notes=data.get("notes", ""),
                )
            except ValidationError as error:
                _form_service_error(form, error)
            else:
                messages.success(request, "Daily flock record saved.")
                return redirect("agriculture:flock_detail", pk=flock.pk)

    return render(
        request,
        "agriculture/records/daily_record_form.html",
        {"form": form, "flock": flock},
    )


@login_required
@egg_production_add_required
def egg_production_create(request, flock_pk):
    flock = get_object_or_404(PoultryFlock, pk=flock_pk)
    form = EggProductionForm(
        request.POST or None,
        user=request.user,
        flock=flock,
    )
    form.instance.flock = flock
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            PoultryService.record_egg_production(
                flock=flock,
                actor=request.user,
                operation=data.get("operation"),
                record_date=data["record_date"],
                eggs_collected=data["eggs_collected"],
                saleable_eggs=data["saleable_eggs"],
                hatching_eggs=data["hatching_eggs"],
                cracked_eggs=data["cracked_eggs"],
                rejected_eggs=data["dirty_or_rejected_eggs"],
                inventory_product=data.get("inventory_product"),
                warehouse=data.get("warehouse"),
                notes=data.get("notes", ""),
            )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            messages.success(request, "Egg production recorded.")
            return redirect("agriculture:flock_detail", pk=flock.pk)

    return render(
        request,
        "agriculture/records/egg_production_form.html",
        {"form": form, "flock": flock},
    )


@login_required
@feeding_add_required
def feeding_record_create(request, flock_pk):
    flock = get_object_or_404(PoultryFlock, pk=flock_pk)
    form = FeedingRecordForm(
        request.POST or None,
        user=request.user,
        flock=flock,
    )
    form.instance.flock = flock
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            if data.get("post_to_finance"):
                require_feeding_finance_post(request.user)

            with transaction.atomic():
                feeding_record = PoultryService.record_feeding(
                    flock=flock,
                    actor=request.user,
                    operation=data.get("operation"),
                    record_date=data["record_date"],
                    feed_product=data["feed_product"],
                    warehouse=data["warehouse"],
                    quantity_kg=data["quantity_kg"],
                    unit_cost=data["unit_cost"],
                    notes=data.get("notes", ""),
                )
                if data.get("post_to_finance"):
                    AgricultureFinanceIntegrationService.post_feeding_cost(
                        feeding_record=feeding_record,
                        account=data["finance_account"],
                        actor=request.user,
                    )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            message = "Feeding record saved."
            if data.get("post_to_finance"):
                message += " Its cost was posted to Finance."
            messages.success(request, message)
            return redirect("agriculture:flock_detail", pk=flock.pk)

    return render(
        request,
        "agriculture/records/feeding_form.html",
        {"form": form, "flock": flock},
    )


@login_required
@health_add_required
def health_record_create(request, flock_pk):
    flock = get_object_or_404(PoultryFlock, pk=flock_pk)
    form = HealthRecordForm(
        request.POST or None,
        user=request.user,
        flock=flock,
    )
    form.instance.flock = flock
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            if data.get("post_to_finance"):
                require_health_finance_post(request.user)

            with transaction.atomic():
                health_record = PoultryService.record_health(
                    flock=flock,
                    actor=request.user,
                    operation=data.get("operation"),
                    record_date=data["record_date"],
                    record_type=data["record_type"],
                    condition_or_vaccine=data["condition_or_vaccine"],
                    medicine_product=data.get("medicine_product"),
                    dosage=data.get("dosage", ""),
                    birds_treated=data["birds_treated"],
                    next_due_date=data.get("next_due_date"),
                    veterinarian_or_provider=data.get(
                        "veterinarian_or_provider",
                        "",
                    ),
                    cost=data["cost"],
                    notes=data.get("notes", ""),
                )
                if data.get("post_to_finance"):
                    AgricultureFinanceIntegrationService.post_health_cost(
                        health_record=health_record,
                        account=data["finance_account"],
                        actor=request.user,
                    )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            message = "Health record saved."
            if data.get("post_to_finance"):
                message += " Its cost was posted to Finance."
            messages.success(request, message)
            return redirect("agriculture:flock_detail", pk=flock.pk)

    return render(
        request,
        "agriculture/records/health_form.html",
        {"form": form, "flock": flock},
    )


@login_required
@mortality_add_required
def mortality_record_create(request, flock_pk):
    flock = get_object_or_404(PoultryFlock, pk=flock_pk)
    form = MortalityRecordForm(
        request.POST or None,
        user=request.user,
        flock=flock,
    )
    form.instance.flock = flock
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            PoultryService.record_mortality(
                flock=flock,
                actor=request.user,
                operation=data.get("operation"),
                record_date=data["record_date"],
                quantity=data["quantity"],
                suspected_cause=data["suspected_cause"],
                health_record=data.get("health_record"),
                action_taken=data.get("action_taken", ""),
                notes=data.get("notes", ""),
            )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            messages.success(request, "Mortality record saved.")
            return redirect("agriculture:flock_detail", pk=flock.pk)

    return render(
        request,
        "agriculture/records/mortality_form.html",
        {"form": form, "flock": flock},
    )


# ---------------------------------------------------------------------------
# Incubation
# ---------------------------------------------------------------------------


@login_required
@incubation_view_required
def incubation_list(request):
    batches = IncubationBatch.objects.select_related(
        "operation",
        "source_flock",
        "incubator_asset",
        "chick_product",
        "output_warehouse",
    )
    status = request.GET.get("status", "").strip().upper()
    if status:
        batches = batches.filter(status=status)

    return render(
        request,
        "agriculture/incubation/incubation_list.html",
        {
            "batches": batches,
            "statuses": IncubationBatch.STATUSES,
            "selected_status": status,
        },
    )


@login_required
@incubation_add_required
def incubation_create(request):
    form = IncubationBatchForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            batch = PoultryService.create_incubation_batch(
                eggs_set=data["eggs_set"],
                set_date=data["set_date"],
                expected_hatch_date=data["expected_hatch_date"],
                actor=request.user,
                operation=data.get("operation"),
                source_flock=data.get("source_flock"),
                incubator_asset=data.get("incubator_asset"),
                chick_product=data.get("chick_product"),
                output_warehouse=data.get("output_warehouse"),
                notes=data.get("notes", ""),
            )
        except ValidationError as error:
            _form_service_error(form, error)
        else:
            messages.success(
                request,
                f"Incubation batch {batch.code} created.",
            )
            return redirect(
                "agriculture:incubation_detail",
                pk=batch.pk,
            )

    return render(
        request,
        "agriculture/incubation/incubation_form.html",
        {"form": form, "title": "Create Incubation Batch"},
    )


@login_required
@incubation_view_required
def incubation_detail(request, pk):
    batch = get_object_or_404(
        IncubationBatch.objects.select_related(
            "operation",
            "source_flock",
            "incubator_asset",
            "chick_product",
            "output_warehouse",
            "stock_movement",
        ),
        pk=pk,
    )
    return render(
        request,
        "agriculture/incubation/incubation_detail.html",
        {
            "batch": batch,
            "candling_form": IncubationCandlingForm(batch=batch),
            "completion_form": IncubationCompletionForm(batch=batch),
        },
    )


@login_required
@incubation_edit_required
@require_POST
def incubation_candle(request, pk):
    batch = get_object_or_404(IncubationBatch, pk=pk)
    form = IncubationCandlingForm(request.POST, batch=batch)
    if form.is_valid():
        try:
            PoultryService.candle_incubation(
                batch=batch,
                actor=request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _validation_messages(request, error)
        else:
            messages.success(request, f"Batch {batch.code} candled.")
    else:
        messages.error(request, form.errors.as_text())

    return redirect("agriculture:incubation_detail", pk=batch.pk)


@login_required
@incubation_edit_required
@require_POST
def incubation_complete(request, pk):
    batch = get_object_or_404(IncubationBatch, pk=pk)
    form = IncubationCompletionForm(request.POST, batch=batch)
    if form.is_valid():
        try:
            PoultryService.complete_incubation(
                batch=batch,
                actor=request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _validation_messages(request, error)
        else:
            messages.success(
                request,
                f"Batch {batch.code} completed.",
            )
    else:
        messages.error(request, form.errors.as_text())

    return redirect("agriculture:incubation_detail", pk=batch.pk)


# ---------------------------------------------------------------------------
# Valuation and management reporting
# ---------------------------------------------------------------------------


@login_required
@reports_view_required
def valuation_report(request):
    farm_id = request.GET.get("farm", "").strip()
    start_value = request.GET.get("start_date", "").strip()
    end_value = request.GET.get("end_date", "").strip()

    farm = None
    if farm_id:
        if not farm_id.isdigit():
            messages.error(request, "Select a valid poultry farm.")
        else:
            farm = get_object_or_404(PoultryFarm, pk=farm_id)

    start_date = parse_date(start_value) if start_value else None
    end_date = parse_date(end_value) if end_value else None

    if start_value and start_date is None:
        messages.error(request, "Enter a valid report start date.")
    if end_value and end_date is None:
        messages.error(request, "Enter a valid report end date.")

    try:
        summary = AgricultureValuationService.portfolio_summary(
            farm=farm,
            start_date=start_date,
            end_date=end_date,
        )
    except ValidationError as error:
        _validation_messages(request, error)
        summary = AgricultureValuationService.portfolio_summary(
            farm=farm,
        )

    context = {
        "summary": summary,
        "farms": PoultryFarm.objects.filter(is_active=True),
        "selected_farm": farm,
        "selected_farm_id": farm_id,
        "start_date": start_value,
        "end_date": end_value,
    }
    return render(
        request,
        "agriculture/reports/valuation_report.html",
        context,
    )