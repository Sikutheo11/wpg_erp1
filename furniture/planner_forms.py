from django import forms

from .planner_models import (
    ProductionPlan, ProductionPlanAdditionalCost,
    ProductionPlanLabour, ProductionPlanMachine, ProductionPlanMaterial,
)


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class ProductionPlanForm(BootstrapModelForm):
    class Meta:
        model = ProductionPlan
        fields = [
            "order", "product", "name", "quantity",
            "default_wastage_rate", "overhead_rate",
            "target_profit_margin", "assumptions",
        ]
        widgets = {"assumptions": forms.Textarea(attrs={"rows": 3})}


class ProductionPlanMaterialForm(BootstrapModelForm):
    class Meta:
        model = ProductionPlanMaterial
        fields = ["raw_material", "quantity_per_unit", "wastage_rate", "note"]


class ProductionPlanLabourForm(BootstrapModelForm):
    class Meta:
        model = ProductionPlanLabour
        fields = ["role_name", "hours_per_unit", "hourly_rate", "note"]


class ProductionPlanMachineForm(BootstrapModelForm):
    class Meta:
        model = ProductionPlanMachine
        fields = ["asset", "hours_per_unit", "hourly_cost", "note"]


class ProductionPlanAdditionalCostForm(BootstrapModelForm):
    class Meta:
        model = ProductionPlanAdditionalCost
        fields = ["cost_type", "description", "amount"]
