from datetime import timedelta

from django import forms
from django.utils import timezone


class ProductionPlanQuotationForm(forms.Form):
    valid_until = forms.DateField(
        initial=lambda: timezone.localdate() + timedelta(days=30),
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    discount = forms.DecimalField(
        min_value=0, decimal_places=2, max_digits=15, initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    tax = forms.DecimalField(
        min_value=0, decimal_places=2, max_digits=15, initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )
