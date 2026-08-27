from django import forms
from inventory.models import Warehouse

class FinishedGoodsReleaseForm(forms.Form):
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.none(), label="Finished-goods warehouse", widget=forms.Select(attrs={"class": "form-select"}))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = Warehouse.objects.filter(is_active=True, business_unit="FURNITURE", warehouse_type="FINISHED_GOODS").order_by("name")
