from django import forms

from .models import (
    Project,
    Site,
    Task,
    ConstructionMaterial,
    ConstructionAssetUsage,
    ConstructionLabour,
    ConstructionExpense
)


# ======================================================
# BOOTSTRAP MIXIN
# ======================================================

class BootstrapFormMixin:

    def apply_bootstrap(self):

        for field_name, field in self.fields.items():

            if isinstance(field.widget, forms.Select):

                field.widget.attrs.update({
                    'class': 'form-select'
                })

            elif isinstance(field.widget, forms.Textarea):

                field.widget.attrs.update({
                    'class': 'form-control',
                    'rows': 4
                })

            else:

                field.widget.attrs.update({
                    'class': 'form-control'
                })


# ======================================================
# PROJECT FORM
# ======================================================

class ProjectForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = Project

        fields = [
            'name',
            'client_name',
            'client_phone',
            'location',
            'start_date',
            'end_date',
            'budget',
            'status',
            'manager',
        ]

        widgets = {

            'start_date': forms.DateInput(
                attrs={'type': 'date'}
            ),

            'end_date': forms.DateInput(
                attrs={'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()


# ======================================================
# SITE FORM
# ======================================================

class SiteForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = Site

        fields = [
            'project',
            'name',
            'location',
            'supervisor',
            'start_date',
            'expected_end_date',
        ]

        widgets = {

            'start_date': forms.DateInput(
                attrs={'type': 'date'}
            ),

            'expected_end_date': forms.DateInput(
                attrs={'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()


# ======================================================
# TASK FORM
# ======================================================

class TaskForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = Task

        fields = [
            'project',
            'site',
            'title',
            'description',
            'assigned_to',
            'status',
            'start_date',
            'due_date',
            'progress',
        ]

        widgets = {

            'start_date': forms.DateInput(
                attrs={'type': 'date'}
            ),

            'due_date': forms.DateInput(
                attrs={'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()


# ======================================================
# MATERIAL USAGE FORM
# ======================================================

class ConstructionMaterialForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = ConstructionMaterial

        fields = [
            'project',
            'raw_material',
            'quantity_used',
            'unit_cost',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()

    def clean(self):

        cleaned_data = super().clean()

        material = cleaned_data.get(
            'raw_material'
        )

        quantity = cleaned_data.get(
            'quantity_used'
        )

        if material and quantity:

            if quantity > material.current_stock:

                raise forms.ValidationError(
                    f"Available stock is only "
                    f"{material.current_stock} "
                    f"{material.unit}"
                )

        return cleaned_data


# ======================================================
# ASSET USAGE FORM
# ======================================================

class ConstructionAssetUsageForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = ConstructionAssetUsage

        fields = [
            'project',
            'asset',
            'hours_used',
            'cost_per_hour',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()


# ======================================================
# LABOUR FORM
# ======================================================

class ConstructionLabourForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = ConstructionLabour

        fields = [
            'project',
            'employee',
            'role',
            'hours_worked',
            'hourly_rate',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()


# ======================================================
# EXPENSE FORM
# ======================================================

class ConstructionExpenseForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = ConstructionExpense

        fields = [
            'project',
            'expense_type',
            'amount',
            'description',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.apply_bootstrap()