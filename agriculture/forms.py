from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from finance.models import Account

from .models import (
    AgricultureOperation,
    DailyFlockRecord,
    EggProduction,
    FeedingRecord,
    HealthRecord,
    IncubationBatch,
    MortalityRecord,
    PoultryBreed,
    PoultryFarm,
    PoultryFlock,
    PoultryHouse,
)


class BootstrapFormMixin:
    """Apply consistent dashboard styling without repeating widget definitions."""

    def _apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(
                widget,
                (
                    forms.Select,
                    forms.SelectMultiple,
                ),
            ):
                css_class = "form-select"
            else:
                css_class = "form-control"

            current = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{current} {css_class}".strip()

            if field.required:
                widget.attrs.setdefault("required", True)


class AgricultureModelForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class PoultryFarmForm(AgricultureModelForm):
    class Meta:
        model = PoultryFarm
        fields = [
            "code",
            "name",
            "location",
            "manager",
            "warehouse",
            "description",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        warehouse_field = self.fields["warehouse"]
        warehouse_model = warehouse_field.queryset.model
        if hasattr(warehouse_model, "business_unit"):
            warehouse_field.queryset = warehouse_field.queryset.filter(
                business_unit="AGRICULTURE"
            )


class PoultryHouseForm(forms.ModelForm):

    class Meta:
        model = PoultryHouse
        fields = [
            "farm",
            "code",
            "name",
            "house_type",
            "capacity",
            "description",
            "is_active",
        ]

        widgets = {
            "farm": forms.Select(
                attrs={"class": "form-select"}
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. HOUSE-001",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "House name",
                }
            ),
            "house_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "capacity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Maximum number of birds",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

        labels = {
            "farm": "Poultry Farm",
            "code": "House Code",
            "name": "House Name",
            "house_type": "House Type",
            "capacity": "Bird Capacity",
            "description": "Description",
            "is_active": "Active",
        }

    def __init__(self, *args, farm=None, user=None, **kwargs):
        self.user = user
        self.fixed_farm = farm

        super().__init__(*args, **kwargs)

        farm_queryset = (
            PoultryFarm.objects
            .filter(is_active=True)
            .select_related("warehouse")
            .order_by("name")
        )

        if self.instance and self.instance.pk:
            farm_queryset = (
                PoultryFarm.objects
                .filter(
                    models.Q(is_active=True)
                    | models.Q(pk=self.instance.farm_id)
                )
                .select_related("warehouse")
                .order_by("name")
            )

        self.fields["farm"].queryset = farm_queryset

        if farm is not None:
            self.fields["farm"].initial = farm
            self.fields["farm"].disabled = True

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")

        if capacity is not None and capacity < 1:
            raise forms.ValidationError(
                "House capacity must be at least one bird."
            )

        return capacity

    def clean(self):
        cleaned_data = super().clean()

        farm = cleaned_data.get("farm")
        code = cleaned_data.get("code")

        if farm and not farm.warehouse_id:
            self.add_error(
                "farm",
                "This farm has no Agriculture warehouse assigned.",
            )

        if farm and code:
            duplicate = PoultryHouse.objects.filter(
                farm=farm,
                code__iexact=code,
            )

            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)

            if duplicate.exists():
                self.add_error(
                    "code",
                    "This house code already exists on the selected farm.",
                )

        return cleaned_data


class PoultryBreedForm(AgricultureModelForm):
    class Meta:
        model = PoultryBreed
        fields = [
            "code",
            "name",
            "breed_type",
            "expected_laying_age_weeks",
            "expected_market_age_weeks",
            "description",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class AgricultureOperationForm(AgricultureModelForm):
    """
    Creates a draft operation.

    Status, actual cost, Finance references, approval and actual dates are
    controlled by AgricultureOperationService and the shared Core workflow.
    """

    class Meta:
        model = AgricultureOperation
        fields = [
            "operation_type",
            "farm",
            "source_order",
            "assigned_to",
            "planned_start_date",
            "planned_end_date",
            "budget",
            "notes",
        ]
        widgets = {
            "planned_start_date": forms.DateInput(attrs={"type": "date"}),
            "planned_end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["farm"].queryset = PoultryFarm.objects.filter(
            is_active=True
        ).order_by("name")

        order_field = self.fields["source_order"]
        order_model = order_field.queryset.model
        if hasattr(order_model, "business_unit"):
            order_field.queryset = order_field.queryset.filter(
                business_unit="AGRICULTURE"
            )


class OperationNoteForm(BootstrapFormMixin, forms.Form):
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Optional workflow note",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class OperationReasonForm(BootstrapFormMixin, forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Reason is required",
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if not reason:
            raise ValidationError("A reason is required.")
        return reason


class PoultryFlockForm(AgricultureModelForm):
    """
    Creates a flock through PoultryService.

    Code, status, current quantity and closing data are service-controlled.
    """

    class Meta:
        model = PoultryFlock
        fields = [
            "source_operation",
            "farm",
            "house",
            "breed",
            "purpose",
            "source",
            "arrival_or_hatch_date",
            "initial_quantity",
            "average_unit_cost",
            "livestock_product",
            "notes",
        ]
        widgets = {
            "arrival_or_hatch_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        farm = kwargs.pop("farm", None)
        super().__init__(*args, **kwargs)

        self.fields["farm"].queryset = PoultryFarm.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["house"].queryset = PoultryHouse.objects.filter(
            is_active=True
        ).select_related("farm")
        self.fields["breed"].queryset = PoultryBreed.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["source_operation"].queryset = (
            AgricultureOperation.objects.filter(
                status__in={"APPROVED", "ACTIVE", "ON_HOLD"}
            ).select_related("farm")
        )

        product_field = self.fields["livestock_product"]
        product_model = product_field.queryset.model
        product_filters = {}
        if hasattr(product_model, "business_unit"):
            product_filters["business_unit"] = "AGRICULTURE"
        if hasattr(product_model, "product_type"):
            product_filters["product_type"] = "LIVESTOCK"
        if product_filters:
            product_field.queryset = product_field.queryset.filter(
                **product_filters
            )

        if farm is not None:
            self.fields["farm"].initial = farm
            self.fields["farm"].disabled = True
            self.fields["house"].queryset = self.fields[
                "house"
            ].queryset.filter(farm=farm)
            self.fields["source_operation"].queryset = self.fields[
                "source_operation"
            ].queryset.filter(farm=farm)

    def clean(self):
        cleaned_data = super().clean()
        farm = cleaned_data.get("farm")
        house = cleaned_data.get("house")
        operation = cleaned_data.get("source_operation")

        if farm and house and house.farm_id != farm.pk:
            self.add_error(
                "house",
                "The selected house must belong to the selected farm.",
            )
        if farm and operation and operation.farm_id != farm.pk:
            self.add_error(
                "source_operation",
                "The operation must belong to the selected farm.",
            )
        return cleaned_data


class DailyFlockRecordForm(AgricultureModelForm):
    class Meta:
        model = DailyFlockRecord
        fields = [
            "operation",
            "record_date",
            "additions",
            "transferred_in",
            "mortality",
            "culls",
            "sold",
            "transferred_out",
            "average_weight_kg",
            "notes",
        ]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        flock = kwargs.pop("flock", None)
        super().__init__(*args, **kwargs)

        queryset = AgricultureOperation.objects.filter(
            status__in={"APPROVED", "ACTIVE", "ON_HOLD"}
        )
        if flock is not None:
            queryset = queryset.filter(farm_id=flock.farm_id)
        self.fields["operation"].queryset = queryset


class EggProductionForm(AgricultureModelForm):
    class Meta:
        model = EggProduction
        fields = [
            "operation",
            "record_date",
            "eggs_collected",
            "saleable_eggs",
            "hatching_eggs",
            "cracked_eggs",
            "dirty_or_rejected_eggs",
            "inventory_product",
            "warehouse",
            "notes",
        ]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        flock = kwargs.pop("flock", None)
        super().__init__(*args, **kwargs)
        self._limit_operation_and_inventory(flock)

    def _limit_operation_and_inventory(self, flock):
        operation_queryset = AgricultureOperation.objects.filter(
            status__in={"APPROVED", "ACTIVE", "ON_HOLD"},
            operation_type="EGG_PRODUCTION",
        )
        if flock is not None:
            operation_queryset = operation_queryset.filter(
                farm_id=flock.farm_id
            )
        self.fields["operation"].queryset = operation_queryset

        product_field = self.fields["inventory_product"]
        product_model = product_field.queryset.model
        if hasattr(product_model, "business_unit"):
            product_field.queryset = product_field.queryset.filter(
                business_unit="AGRICULTURE"
            )

        warehouse_field = self.fields["warehouse"]
        warehouse_model = warehouse_field.queryset.model
        if hasattr(warehouse_model, "business_unit"):
            warehouse_field.queryset = warehouse_field.queryset.filter(
                business_unit="AGRICULTURE"
            )


class FeedingRecordForm(AgricultureModelForm):
    post_to_finance = forms.BooleanField(
        required=False,
        label="Post this feeding cost to Finance",
    )
    finance_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        required=False,
        label="Finance Account",
        help_text="Account that will fund this operating expense.",
    )

    class Meta:
        model = FeedingRecord
        fields = [
            "operation",
            "record_date",
            "feed_product",
            "warehouse",
            "quantity_kg",
            "unit_cost",
            "notes",
        ]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        flock = kwargs.pop("flock", None)
        super().__init__(*args, **kwargs)

        operations = AgricultureOperation.objects.filter(
            status__in={"APPROVED", "ACTIVE", "ON_HOLD"},
            operation_type="FEEDING",
        )
        if flock is not None:
            operations = operations.filter(farm_id=flock.farm_id)
        self.fields["operation"].queryset = operations

        product_field = self.fields["feed_product"]
        product_model = product_field.queryset.model
        if hasattr(product_model, "business_unit"):
            product_field.queryset = product_field.queryset.filter(
                business_unit="AGRICULTURE"
            )

        warehouse_field = self.fields["warehouse"]
        warehouse_model = warehouse_field.queryset.model
        if hasattr(warehouse_model, "business_unit"):
            warehouse_field.queryset = warehouse_field.queryset.filter(
                business_unit="AGRICULTURE"
            )

        account_queryset = Account.objects.all()
        account_fields = {
            field.name
            for field in Account._meta.get_fields()
        }
        if "is_active" in account_fields:
            account_queryset = account_queryset.filter(is_active=True)
        self.fields["finance_account"].queryset = account_queryset.order_by(
            "name"
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("post_to_finance"):
            if cleaned_data.get("finance_account") is None:
                self.add_error(
                    "finance_account",
                    "Select the Finance account for this expense.",
                )
            if cleaned_data.get("operation") is None:
                self.add_error(
                    "operation",
                    "Finance posting requires an Agriculture operation.",
                )
            quantity = cleaned_data.get("quantity_kg")
            unit_cost = cleaned_data.get("unit_cost")
            if quantity is not None and unit_cost is not None:
                if quantity * unit_cost <= 0:
                    self.add_error(
                        "unit_cost",
                        "Finance posting requires a cost greater than zero.",
                    )
        return cleaned_data


class HealthRecordForm(AgricultureModelForm):
    post_to_finance = forms.BooleanField(
        required=False,
        label="Post this health cost to Finance",
    )
    finance_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        required=False,
        label="Finance Account",
        help_text="Account that will fund this health expense.",
    )

    class Meta:
        model = HealthRecord
        fields = [
            "operation",
            "record_date",
            "record_type",
            "condition_or_vaccine",
            "medicine_product",
            "dosage",
            "birds_treated",
            "next_due_date",
            "veterinarian_or_provider",
            "cost",
            "notes",
        ]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "next_due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        flock = kwargs.pop("flock", None)
        super().__init__(*args, **kwargs)

        operations = AgricultureOperation.objects.filter(
            status__in={"APPROVED", "ACTIVE", "ON_HOLD"},
            operation_type="HEALTH",
        )
        if flock is not None:
            operations = operations.filter(farm_id=flock.farm_id)
        self.fields["operation"].queryset = operations

        product_field = self.fields["medicine_product"]
        product_model = product_field.queryset.model
        if hasattr(product_model, "business_unit"):
            product_field.queryset = product_field.queryset.filter(
                business_unit="AGRICULTURE"
            )

        account_queryset = Account.objects.all()
        account_fields = {
            field.name
            for field in Account._meta.get_fields()
        }
        if "is_active" in account_fields:
            account_queryset = account_queryset.filter(is_active=True)
        self.fields["finance_account"].queryset = account_queryset.order_by(
            "name"
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("post_to_finance"):
            if cleaned_data.get("finance_account") is None:
                self.add_error(
                    "finance_account",
                    "Select the Finance account for this expense.",
                )
            if cleaned_data.get("operation") is None:
                self.add_error(
                    "operation",
                    "Finance posting requires an Agriculture operation.",
                )
            cost = cleaned_data.get("cost")
            if cost is not None and cost <= 0:
                self.add_error(
                    "cost",
                    "Finance posting requires a cost greater than zero.",
                )
        return cleaned_data


class MortalityRecordForm(AgricultureModelForm):
    class Meta:
        model = MortalityRecord
        fields = [
            "operation",
            "record_date",
            "quantity",
            "suspected_cause",
            "health_record",
            "action_taken",
            "notes",
        ]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
            "action_taken": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        flock = kwargs.pop("flock", None)
        super().__init__(*args, **kwargs)

        operations = AgricultureOperation.objects.filter(
            status__in={"APPROVED", "ACTIVE", "ON_HOLD"}
        )
        health_records = HealthRecord.objects.none()
        if flock is not None:
            operations = operations.filter(farm_id=flock.farm_id)
            health_records = HealthRecord.objects.filter(flock=flock)

        self.fields["operation"].queryset = operations
        self.fields["health_record"].queryset = health_records

        if flock is not None:
            self.fields["quantity"].widget.attrs["max"] = flock.current_quantity


class IncubationBatchForm(AgricultureModelForm):
    """Creates a batch; candling and completion use their dedicated forms."""

    class Meta:
        model = IncubationBatch
        fields = [
            "operation",
            "source_flock",
            "incubator_asset",
            "eggs_set",
            "set_date",
            "expected_hatch_date",
            "chick_product",
            "output_warehouse",
            "notes",
        ]
        widgets = {
            "set_date": forms.DateInput(attrs={"type": "date"}),
            "expected_hatch_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["operation"].queryset = (
            AgricultureOperation.objects.filter(
                status__in={"APPROVED", "ACTIVE", "ON_HOLD"},
                operation_type="INCUBATION",
            )
        )
        self.fields["source_flock"].queryset = PoultryFlock.objects.filter(
            status__in={"ACTIVE", "QUARANTINED"},
            purpose__in={"LAYERS", "BREEDERS", "DUAL_PURPOSE"},
        )

        product_field = self.fields["chick_product"]
        product_model = product_field.queryset.model
        filters = {}
        if hasattr(product_model, "business_unit"):
            filters["business_unit"] = "AGRICULTURE"
        if hasattr(product_model, "product_type"):
            filters["product_type"] = "LIVESTOCK"
        if filters:
            product_field.queryset = product_field.queryset.filter(**filters)

        warehouse_field = self.fields["output_warehouse"]
        warehouse_model = warehouse_field.queryset.model
        if hasattr(warehouse_model, "business_unit"):
            warehouse_field.queryset = warehouse_field.queryset.filter(
                business_unit="AGRICULTURE"
            )

    def clean(self):
        cleaned_data = super().clean()
        operation = cleaned_data.get("operation")
        flock = cleaned_data.get("source_flock")
        if operation and flock and operation.farm_id != flock.farm_id:
            self.add_error(
                "operation",
                "The operation and source flock must belong to the same farm.",
            )
        return cleaned_data


class IncubationCandlingForm(BootstrapFormMixin, forms.Form):
    eggs_candled = forms.IntegerField(min_value=1)
    fertile_eggs = forms.IntegerField(min_value=0)
    infertile_eggs = forms.IntegerField(min_value=0)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, batch=None, **kwargs):
        self.batch = batch
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

        if batch is not None:
            self.fields["eggs_candled"].widget.attrs["max"] = batch.eggs_set

    def clean(self):
        cleaned_data = super().clean()
        candled = cleaned_data.get("eggs_candled")
        fertile = cleaned_data.get("fertile_eggs")
        infertile = cleaned_data.get("infertile_eggs")

        if None not in (candled, fertile, infertile):
            if fertile + infertile > candled:
                raise ValidationError(
                    "Fertile and infertile eggs cannot exceed candled eggs."
                )
            if self.batch and candled > self.batch.eggs_set:
                self.add_error(
                    "eggs_candled",
                    "Candled eggs cannot exceed eggs set.",
                )
        return cleaned_data


class IncubationCompletionForm(BootstrapFormMixin, forms.Form):
    actual_hatch_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    chicks_hatched = forms.IntegerField(min_value=0)
    unhatched_eggs = forms.IntegerField(min_value=0)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, batch=None, **kwargs):
        self.batch = batch
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

        if not self.is_bound:
            self.fields["actual_hatch_date"].initial = timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()
        chicks = cleaned_data.get("chicks_hatched")
        unhatched = cleaned_data.get("unhatched_eggs")

        if self.batch and chicks is not None:
            if chicks > self.batch.fertile_eggs:
                self.add_error(
                    "chicks_hatched",
                    "Hatched chicks cannot exceed fertile eggs.",
                )
        if self.batch and None not in (chicks, unhatched):
            if chicks + unhatched > self.batch.eggs_set:
                raise ValidationError(
                    "Hatched chicks and unhatched eggs cannot exceed eggs set."
                )
        return cleaned_data