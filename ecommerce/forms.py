from django import forms


class CheckoutForm(forms.Form):

    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Full Name"
        })
    )

    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Phone Number"
        })
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email Address"
        })
    )

    province = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    district = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    sector = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    cell = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    village = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "class": "form-control",
            "placeholder": "Delivery Address"
        })
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "class": "form-control",
            "placeholder": "Additional Notes"
        })
    )