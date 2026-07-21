from django import forms
from .models import Order, OrderItem


class RestockOrderForm(forms.ModelForm):

    class Meta:
        model = Order

        fields = [
            "customer_name",
            "customer_phone",
            "notes",
        ]

        widgets = {
            "customer_name": forms.TextInput(attrs={
                "class": "form-control",
                "value": "WPG Internal Production"
            }),
            "customer_phone": forms.TextInput(attrs={
                "class": "form-control",
                "value": "N/A"
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Reason for restock / production notes"
            }),
        }


class RestockOrderItemForm(forms.ModelForm):

    class Meta:
        model = OrderItem

        fields = [
            "product",
            "quantity",
            "price",
        ]

        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
        }