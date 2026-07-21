from django.db import models
from django import forms
from Employee.models import Employee
from .models import (
    Order,
    ProductionJob,
    Quotation,
    BillOfMaterial,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
    StockReservation,
    ProductionOutput,
    ProductionTask,
    ProductionChecklist,
    ProductionTaskProgress,
    ProductionSettings,
    QualityInspection,
    ProductionDefect,
    ReworkOrder,
    
)
# ======================================================
# COMMON HELPERS
# ======================================================

def employee_queryset():
    """
    Employees displayed consistently in assignment forms.
    """
    return (
        Employee.objects.select_related(
            "user",
            "department",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )


# ======================================================
# LEGACY CUSTOMER ORDER FORM
# Temporary until furniture.Order is fully retired.
# ======================================================

class OrderForm(forms.ModelForm):

    class Meta:
        model = Order

        fields = [
            "product",
            "customer_name",
            "customer_phone",
            "quantity_to_produce",
        ]

        widgets = {
            "product": forms.Select(
                attrs={"class": "form-select"}
            ),
            "customer_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer name",
                }
            ),
            "customer_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer phone number",
                }
            ),
            "quantity_to_produce": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
        }

    def clean_quantity_to_produce(self):
        quantity = self.cleaned_data["quantity_to_produce"]

        if quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least one."
            )

        return quantity


# ======================================================
# LEGACY ORDER WORKER ASSIGNMENT
# ======================================================

class AssignWorkerForm(forms.ModelForm):

    class Meta:
        model = Order

        fields = [
            "assigned_to",
        ]

        widgets = {
            "assigned_to": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["assigned_to"].queryset = employee_queryset()


# ======================================================
# PRODUCTION JOB FORM
# ======================================================

class ProductionJobForm(forms.ModelForm):
    class Meta:
        model = ProductionJob

        fields = [
            "order",
            "product",
            "job_type",
            "quantity_to_produce",
            "assigned_to",
            "description",
            "expected_end_date",
        ]

        widgets = {
            "order": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "product": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "job_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "quantity_to_produce": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "assigned_to": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe this production job",
                }
            ),
            "expected_end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["assigned_to"].queryset = (
            employee_queryset()
        )

        self.fields["assigned_to"].required = False
        self.fields["order"].required = False
        self.fields["product"].required = False

        self.fields["expected_end_date"].input_formats = [
            "%Y-%m-%d",
        ]

        # Get the actual Order model linked to ProductionJob.order.
        OrderModel = (
            ProductionJob
            ._meta
            .get_field("order")
            .remote_field
            .model
        )

        # Find all order IDs already used by production jobs.
        used_order_ids = (
            ProductionJob.objects
            .exclude(order__isnull=True)
            .values_list(
                "order_id",
                flat=True,
            )
        )

        # Create form:
        # show only orders that do not yet have a production job.
        available_orders = (
            OrderModel.objects
            .exclude(pk__in=used_order_ids)
        )

        # Edit form:
        # keep the current order visible.
        if (
            self.instance
            and self.instance.pk
            and self.instance.order_id
        ):
            current_order = (
                OrderModel.objects
                .filter(pk=self.instance.order_id)
            )

            available_orders = (
                available_orders
                | current_order
            )

        self.fields["order"].queryset = (
            available_orders
            .distinct()
            .order_by("-id")
        )

        self.fields["order"].empty_label = (
            "Select customer order"
        )

    def clean_quantity_to_produce(self):
        quantity = self.cleaned_data.get(
            "quantity_to_produce"
        )

        if quantity is None or quantity < 1:
            raise forms.ValidationError(
                "Quantity to produce must be at least one."
            )

        return quantity

    def clean(self):
        cleaned_data = super().clean()

        order = cleaned_data.get("order")
        product = cleaned_data.get("product")
        job_type = cleaned_data.get("job_type")

        if not order and not product:
            raise forms.ValidationError(
                "Select either a customer order or a product."
            )

        if order:
            existing_job = (
                ProductionJob.objects
                .filter(order=order)
            )

            if self.instance and self.instance.pk:
                existing_job = (
                    existing_job
                    .exclude(pk=self.instance.pk)
                )

            if existing_job.exists():
                self.add_error(
                    "order",
                    (
                        "This customer order already has "
                        "a production job."
                    ),
                )

        if (
            job_type
            in {
                "CUSTOMER_CUSTOM",
                "BACKORDER",
            }
            and not order
        ):
            self.add_error(
                "order",
                (
                    "This job type requires "
                    "a customer order."
                ),
            )

        if (
            job_type
            in {
                "RESTOCK",
                "NEW_PRODUCT",
            }
            and not product
        ):
            self.add_error(
                "product",
                (
                    "This job type requires "
                    "a product."
                ),
            )

        # If an order is selected and product is empty,
        # use the product linked to the order when available.
        if order and not product:
            order_product = getattr(
                order,
                "product",
                None,
            )

            if order_product is not None:
                cleaned_data["product"] = order_product

        return cleaned_data

# ======================================================
# QUOTATION FORM
# ======================================================

class QuotationForm(forms.ModelForm):
    """
    Furniture quotation preparation form.

    Status is controlled by QuotationService, not directly
    by the worker entering costs.
    """

    class Meta:
        model = Quotation

        fields = [
            "production_job",
            "material_cost",
            "labour_cost",
            "machine_cost",
            "transport_cost",
            "other_cost",
            "profit",
            "profit_margin",
            "selling_price",
        ]

        widgets = {
            "production_job": forms.Select(
                attrs={"class": "form-select"}
            ),
            "material_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "labour_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "machine_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "transport_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "other_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "profit": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "profit_margin": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                    "placeholder": "Optional percentage",
                }
            ),
            "selling_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        production_job = kwargs.pop("production_job", None)

        super().__init__(*args, **kwargs)

        if production_job is not None:
            self.fields["production_job"].initial = production_job
            self.fields["production_job"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        money_fields = [
            "material_cost",
            "labour_cost",
            "machine_cost",
            "transport_cost",
            "other_cost",
            "profit",
            "profit_margin",
            "selling_price",
        ]

        for field_name in money_fields:
            value = cleaned_data.get(field_name)

            if value is not None and value < 0:
                self.add_error(
                    field_name,
                    "This value cannot be negative.",
                )

        return cleaned_data


# ======================================================
# QUOTATION APPROVAL FORM
# ======================================================

class QuotationApprovalForm(forms.ModelForm):

    class Meta:
        model = Quotation

        fields = [
            "status",
        ]

        widgets = {
            "status": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def clean_status(self):
        status = self.cleaned_data["status"]

        allowed_statuses = {
            "APPROVED",
            "REJECTED",
        }

        if status not in allowed_statuses:
            raise forms.ValidationError(
                "Select either Approved or Rejected."
            )

        return status


# ======================================================
# BILL OF MATERIAL FORM
# ======================================================

class BillOfMaterialForm(forms.ModelForm):

    class Meta:
        model = BillOfMaterial

        fields = [
            "product",
            "raw_material",
            "quantity_required",
        ]

        widgets = {
            "product": forms.Select(
                attrs={"class": "form-select"}
            ),
            "raw_material": forms.Select(
                attrs={"class": "form-select"}
            ),
            "quantity_required": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0.01,
                    "step": "0.01",
                }
            ),
        }

    def clean_quantity_required(self):
        quantity = self.cleaned_data["quantity_required"]

        if quantity <= 0:
            raise forms.ValidationError(
                "Required quantity must be greater than zero."
            )

        return quantity


# ======================================================
# MATERIAL CONSUMPTION FORM
# ======================================================

class ProductionMaterialForm(forms.ModelForm):

    class Meta:
        model = ProductionMaterial

        fields = [
            "raw_material",
            "quantity_used",
        ]

        widgets = {
            "raw_material": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "quantity_used": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
        }

    def clean_quantity_used(self):
        quantity = self.cleaned_data.get(
            "quantity_used"
        )

        if quantity is None or quantity <= 0:
            raise forms.ValidationError(
                "Quantity used must be greater than zero."
            )

        return quantity


# ======================================================
# LABOUR FORM
# ======================================================

class ProductionLabourForm(forms.ModelForm):

    class Meta:
        model = ProductionLabour

        fields = [
            "employee",
            "hours_worked",
            "hourly_rate",
        ]

        widgets = {
            "employee": forms.Select(
                attrs={"class": "form-select"}
            ),
            "hours_worked": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0.01,
                    "step": "0.25",
                }
            ),
            "hourly_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["employee"].queryset = employee_queryset()

    def clean_hours_worked(self):
        hours = self.cleaned_data["hours_worked"]

        if hours <= 0:
            raise forms.ValidationError(
                "Hours worked must be greater than zero."
            )

        return hours

    def clean_hourly_rate(self):
        rate = self.cleaned_data["hourly_rate"]

        if rate < 0:
            raise forms.ValidationError(
                "Hourly rate cannot be negative."
            )

        return rate


# ======================================================
# MACHINE USAGE FORM
# ======================================================

class ProductionMachineForm(forms.ModelForm):

    class Meta:
        model = ProductionMachine

        fields = [
            "asset",
            "hours_used",
            "hourly_cost",
        ]

        widgets = {
            "asset": forms.Select(
                attrs={"class": "form-select"}
            ),
            "hours_used": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0.01,
                    "step": "0.25",
                }
            ),
            "hourly_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
        }

    def clean_hours_used(self):
        hours = self.cleaned_data["hours_used"]

        if hours <= 0:
            raise forms.ValidationError(
                "Machine hours must be greater than zero."
            )

        return hours

    def clean_hourly_cost(self):
        cost = self.cleaned_data["hourly_cost"]

        if cost < 0:
            raise forms.ValidationError(
                "Hourly machine cost cannot be negative."
            )

        return cost


# ======================================================
# STOCK RESERVATION FORM
# ======================================================

class StockReservationForm(forms.ModelForm):

    class Meta:
        model = StockReservation

        fields = [
            "raw_material",
            "quantity",
        ]

        widgets = {
            "raw_material": forms.Select(
                attrs={"class": "form-select"}
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0.01,
                    "step": "0.01",
                }
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity <= 0:
            raise forms.ValidationError(
                "Reserved quantity must be greater than zero."
            )

        return quantity


# ======================================================
# PRODUCTION OUTPUT FORM
# ======================================================

class ProductionOutputForm(forms.ModelForm):

    class Meta:
        model = ProductionOutput

        fields = [
            "product",
            "quantity_produced",
            "image",
        ]

        widgets = {
            "product": forms.Select(
                attrs={"class": "form-select"}
            ),
            "quantity_produced": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),
        }

    def clean_quantity_produced(self):
        quantity = self.cleaned_data["quantity_produced"]

        if quantity < 1:
            raise forms.ValidationError(
                "Produced quantity must be at least one."
            )

        return quantity


# ======================================================
# PRODUCTION TASK FORM
# ======================================================

class ProductionTaskForm(forms.ModelForm):

    class Meta:
        model = ProductionTask

        fields = [
            "production_job",
            "name",
            "task_type",
            "description",
            "sequence",
            "priority",
            "assigned_to",
            "planned_hours",
            "planned_start",
            "planned_end",
        ]

        widgets = {
            "production_job": forms.Select(
                attrs={"class": "form-select"}
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Cutting, Assembly or Sanding",
                }
            ),
            "task_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the work to be completed",
                }
            ),
            "sequence": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "priority": forms.Select(
                attrs={"class": "form-select"}
            ),
            "assigned_to": forms.Select(
                attrs={"class": "form-select"}
            ),
            "planned_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.25",
                }
            ),
            "planned_start": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "planned_end": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        production_job = kwargs.pop("production_job", None)

        super().__init__(*args, **kwargs)

        self.fields["assigned_to"].queryset = employee_queryset()
        self.fields["assigned_to"].required = False

        self.fields["planned_start"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        self.fields["planned_end"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        if production_job is not None:
            self.fields["production_job"].initial = production_job
            self.fields["production_job"].widget = forms.HiddenInput()

            if not self.instance.pk:
                last_sequence = (
                    production_job.tasks.order_by("-sequence")
                    .values_list("sequence", flat=True)
                    .first()
                    or 0
                )

                self.fields["sequence"].initial = last_sequence + 1

    def clean_sequence(self):
        sequence = self.cleaned_data["sequence"]

        if sequence < 1:
            raise forms.ValidationError(
                "Task sequence must be at least one."
            )

        return sequence

    def clean_planned_hours(self):
        hours = self.cleaned_data["planned_hours"]

        if hours < 0:
            raise forms.ValidationError(
                "Planned hours cannot be negative."
            )

        return hours

    def clean(self):
        cleaned_data = super().clean()

        production_job = cleaned_data.get("production_job")
        sequence = cleaned_data.get("sequence")
        planned_start = cleaned_data.get("planned_start")
        planned_end = cleaned_data.get("planned_end")

        if (
            planned_start
            and planned_end
            and planned_end < planned_start
        ):
            self.add_error(
                "planned_end",
                "Planned end cannot be before planned start.",
            )

        if production_job and sequence:
            duplicate = ProductionTask.objects.filter(
                production_job=production_job,
                sequence=sequence,
            )

            if self.instance.pk:
                duplicate = duplicate.exclude(
                    pk=self.instance.pk
                )

            if duplicate.exists():
                self.add_error(
                    "sequence",
                    "This task sequence is already used in this job.",
                )

        return cleaned_data


# ======================================================
# PRODUCTION TASK ASSIGNMENT FORM
# ======================================================

class ProductionTaskAssignmentForm(forms.Form):

    employee = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Optional assignment note",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["employee"].queryset = employee_queryset()


# ======================================================
# PRODUCTION TASK PROGRESS + PHOTO EVIDENCE
# ======================================================

class ProductionTaskProgressForm(forms.ModelForm):

    class Meta:
        model = ProductionTaskProgress

        fields = [
            "progress_percentage",
            "hours_worked",
            "image",
            "note",
        ]

        widgets = {
            "progress_percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 100,
                    "placeholder": "Progress percentage",
                }
            ),
            "hours_worked": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.25",
                    "placeholder": "Hours worked in this update",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Describe work completed and any challenges"
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task", None)

        super().__init__(*args, **kwargs)

        if self.task is not None:
            self.fields["progress_percentage"].initial = (
                self.task.progress_percentage
            )

    def clean_progress_percentage(self):
        progress = self.cleaned_data["progress_percentage"]

        if progress < 0 or progress > 100:
            raise forms.ValidationError(
                "Progress must be between 0 and 100."
            )

        if (
            self.task is not None
            and progress < self.task.progress_percentage
        ):
            raise forms.ValidationError(
                "Progress cannot be lower than current task progress."
            )

        return progress

    def clean_hours_worked(self):
        hours = self.cleaned_data.get("hours_worked")

        if hours is None:
            return 0

        if hours < 0:
            raise forms.ValidationError(
                "Hours worked cannot be negative."
            )

        return hours

    def clean(self):
        cleaned_data = super().clean()

        progress = cleaned_data.get("progress_percentage")
        image = cleaned_data.get("image")

        if (
            progress is not None
            and self.task is not None
            and progress > self.task.progress_percentage
            and not image
        ):
            self.add_error(
                "image",
                "Attach a photo showing the current work progress.",
            )

        return cleaned_data


# ======================================================
# GENERIC TASK ACTION FORM
# Used by pause, resume, cancel and complete actions.
# ======================================================

class ProductionTaskActionForm(forms.Form):

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Action note or reason",
            }
        ),
    )


# ======================================================
# BLOCK TASK FORM
# Blocking requires a reason.
# ======================================================

class ProductionTaskBlockForm(forms.Form):

    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Explain why this task is blocked",
            }
        ),
    )


# ======================================================
# PRODUCTION CHECKLIST FORM
# ======================================================

class ProductionChecklistForm(forms.ModelForm):

    class Meta:
        model = ProductionChecklist

        fields = [
            "title",
            "is_required",
            "order",
            "note",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Checklist item",
                }
            ),
            "is_required": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Optional checklist note",
                }
            ),
        }

    def clean_order(self):
        order = self.cleaned_data["order"]

        if order < 1:
            raise forms.ValidationError(
                "Checklist order must be at least one."
            )

        return order

class ProductionSettingsForm(forms.ModelForm):

    class Meta:
        model = ProductionSettings

        fields = [
            "overhead_rate",
            "wastage_rate",
            "default_transport_cost",
            "default_other_cost",
            "default_labour_hourly_rate",
            "default_machine_hourly_cost",
            "vat_rate",
            "target_profit_margin",
            "currency",
            "is_active",
        ]

        widgets = {
            "overhead_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "wastage_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "default_transport_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "default_other_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "default_labour_hourly_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "default_machine_hourly_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "vat_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "target_profit_margin": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "currency": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "RWF",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

# ======================================================
# QUALITY INSPECTION FORM
# ======================================================

class QualityInspectionForm(forms.ModelForm):

    class Meta:
        model = QualityInspection

        fields = [
            "production_job",
            "inspection_type",
            "inspector",
            "quantity_inspected",
            "remarks",
            "evidence_image",
        ]

        widgets = {
            "production_job": forms.Select(
                attrs={"class": "form-select"}
            ),
            "inspection_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "inspector": forms.Select(
                attrs={"class": "form-select"}
            ),
            "quantity_inspected": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Inspection preparation notes",
                }
            ),
            "evidence_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        production_job = kwargs.pop(
            "production_job",
            None,
        )

        super().__init__(*args, **kwargs)

        self.fields["inspector"].queryset = (
            employee_queryset()
        )

        if production_job is not None:
            self.fields["production_job"].initial = (
                production_job
            )

            self.fields["production_job"].widget = (
                forms.HiddenInput()
            )

            if not self.is_bound:
                self.fields[
                    "quantity_inspected"
                ].initial = (
                    production_job.quantity_to_produce
                )

    def clean_quantity_inspected(self):
        quantity = self.cleaned_data[
            "quantity_inspected"
        ]

        if quantity < 0:
            raise forms.ValidationError(
                "Quantity inspected cannot be negative."
            )

        return quantity


# ======================================================
# QUALITY RESULT FORM
# ======================================================

class QualityInspectionResultForm(forms.ModelForm):

    class Meta:
        model = QualityInspection

        fields = [
            "result",
            "score",
            "quantity_inspected",
            "quantity_passed",
            "quantity_failed",
            "inspector",
            "remarks",
            "evidence_image",
        ]

        widgets = {
            "result": forms.Select(
                attrs={"class": "form-select"}
            ),
            "score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 100,
                }
            ),
            "quantity_inspected": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "quantity_passed": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "quantity_failed": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "inspector": forms.Select(
                attrs={"class": "form-select"}
            ),
            "remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Inspection findings",
                }
            ),
            "evidence_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["inspector"].queryset = (
            employee_queryset()
        )

    def clean(self):
        cleaned_data = super().clean()

        result = cleaned_data.get("result")
        score = cleaned_data.get("score")
        inspected = cleaned_data.get(
            "quantity_inspected"
        )
        passed = cleaned_data.get(
            "quantity_passed"
        )
        failed = cleaned_data.get(
            "quantity_failed"
        )

        numeric_values = [
            inspected,
            passed,
            failed,
        ]

        if any(
            value is not None and value < 0
            for value in numeric_values
        ):
            raise forms.ValidationError(
                "Inspection quantities cannot be negative."
            )

        if (
            inspected is not None
            and passed is not None
            and failed is not None
            and passed + failed > inspected
        ):
            raise forms.ValidationError(
                "Passed and failed quantities cannot exceed inspected quantity."
            )

        if (
            result == "PASSED"
            and failed is not None
            and failed > 0
        ):
            self.add_error(
                "result",
                "A passed inspection cannot include failed units.",
            )

        if (
            score is not None
            and not 0 <= score <= 100
        ):
            self.add_error(
                "score",
                "Score must be between 0 and 100.",
            )

        return cleaned_data

# ======================================================
# PRODUCTION DEFECT FORM
# ======================================================

class ProductionDefectForm(forms.ModelForm):

    rework_required = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    class Meta:
        model = ProductionDefect

        fields = [
            "defect_type",
            "severity",
            "description",
            "affected_quantity",
            "root_cause",
            "corrective_action",
            "evidence_image",
        ]

        widgets = {
            "defect_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "severity": forms.Select(
                attrs={"class": "form-select"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the quality defect",
                }
            ),
            "affected_quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "root_cause": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Known or suspected root cause",
                }
            ),
            "corrective_action": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Recommended corrective action",
                }
            ),
            "evidence_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),
        }

    def clean_affected_quantity(self):
        quantity = self.cleaned_data[
            "affected_quantity"
        ]

        if quantity <= 0:
            raise forms.ValidationError(
                "Affected quantity must be greater than zero."
            )

        return quantity

# ======================================================
# REWORK ASSIGNMENT FORM
# ======================================================

class ReworkOrderForm(forms.ModelForm):

    class Meta:
        model = ReworkOrder

        fields = [
            "assigned_to",
            "instructions",
            "estimated_hours",
        ]

        widgets = {
            "assigned_to": forms.Select(
                attrs={"class": "form-select"}
            ),
            "instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Rework instructions",
                }
            ),
            "estimated_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.25",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["assigned_to"].queryset = (
            employee_queryset()
        )

    def clean_estimated_hours(self):
        hours = self.cleaned_data[
            "estimated_hours"
        ]

        if hours < 0:
            raise forms.ValidationError(
                "Estimated hours cannot be negative."
            )

        return hours

# ======================================================
# COMPLETE REWORK FORM
# ======================================================

class ReworkCompletionForm(forms.ModelForm):

    class Meta:
        model = ReworkOrder

        fields = [
            "actual_hours",
            "rework_cost",
            "completion_note",
            "completion_image",
        ]

        widgets = {
            "actual_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.25",
                }
            ),
            "rework_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                }
            ),
            "completion_note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the completed rework",
                }
            ),
            "completion_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "capture": "environment",
                }
            ),
        }

    def clean_actual_hours(self):
        hours = self.cleaned_data[
            "actual_hours"
        ]

        if hours < 0:
            raise forms.ValidationError(
                "Actual hours cannot be negative."
            )

        return hours

    def clean_rework_cost(self):
        cost = self.cleaned_data[
            "rework_cost"
        ]

        if cost < 0:
            raise forms.ValidationError(
                "Rework cost cannot be negative."
            )

        return cost

# ======================================================
# VERIFY REWORK FORM
# ======================================================

class ReworkVerificationForm(forms.Form):

    passed = forms.TypedChoiceField(
        choices=(
            (True, "Passed"),
            (False, "Failed"),
        ),
        coerce=lambda value: value == "True",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Verification notes",
            }
        ),
    )