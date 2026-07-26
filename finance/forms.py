from django import forms

from .models import (
    Account,
    Income,
    Expense,
    Receivable,
    Payable,
    Payment,
    Payroll,
)


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "name",
            "account_type",
            "account_number",
            "balance",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account name",
                }
            ),
            "account_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account number",
                }
            ),
            "balance": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
        }


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = [
            "account",
            "title",
            "income_type",
            "amount",
            "date",
            "sale",
        ]
        widgets = {
            "account": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Income title",
                }
            ),
            "income_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "sale": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["sale"].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None or amount <= 0:
            raise forms.ValidationError(
                "Income amount must be greater than zero."
            )

        return amount


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            "account",
            "title",
            "expense_type",
            "amount",
            "date",
            "supplier",
        ]
        widgets = {
            "account": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Expense title",
                }
            ),
            "expense_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "supplier": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["supplier"].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None or amount <= 0:
            raise forms.ValidationError(
                "Expense amount must be greater than zero."
            )

        return amount


class ReceivableForm(forms.ModelForm):
    class Meta:
        model = Receivable
        fields = [
            "order",
            "customer",
            "invoice_number",
            "total_amount",
            "amount_paid",
            "due_date",
            "status",
        ]
        widgets = {
            "order": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "customer": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "invoice_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Invoice number",
                }
            ),
            "total_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "amount_paid": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["due_date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["order"].required = False
        self.fields["customer"].required = False
        self.fields["status"].required = False

    def clean(self):
        cleaned_data = super().clean()

        total_amount = cleaned_data.get(
            "total_amount"
        )
        amount_paid = cleaned_data.get(
            "amount_paid"
        )

        if (
            total_amount is not None
            and total_amount < 0
        ):
            self.add_error(
                "total_amount",
                "Total amount cannot be negative.",
            )

        if (
            amount_paid is not None
            and amount_paid < 0
        ):
            self.add_error(
                "amount_paid",
                "Amount paid cannot be negative.",
            )

        if (
            total_amount is not None
            and amount_paid is not None
            and amount_paid > total_amount
        ):
            self.add_error(
                "amount_paid",
                (
                    "Amount paid cannot exceed "
                    "the total amount."
                ),
            )

        return cleaned_data


class PayableForm(forms.ModelForm):
    class Meta:
        model = Payable
        fields = [
            "supplier",
            "reference",
            "total_amount",
            "amount_paid",
            "due_date",
            "status",
        ]
        widgets = {
            "supplier": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Payable reference",
                }
            ),
            "total_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "amount_paid": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["due_date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["status"].required = False

    def clean(self):
        cleaned_data = super().clean()

        total_amount = cleaned_data.get(
            "total_amount"
        )
        amount_paid = cleaned_data.get(
            "amount_paid"
        )

        if (
            total_amount is not None
            and total_amount < 0
        ):
            self.add_error(
                "total_amount",
                "Total amount cannot be negative.",
            )

        if (
            amount_paid is not None
            and amount_paid < 0
        ):
            self.add_error(
                "amount_paid",
                "Amount paid cannot be negative.",
            )

        if (
            total_amount is not None
            and amount_paid is not None
            and amount_paid > total_amount
        ):
            self.add_error(
                "amount_paid",
                (
                    "Amount paid cannot exceed "
                    "the total amount."
                ),
            )

        return cleaned_data


class PaymentForm(forms.ModelForm):
    """
    General payment form.

    Payment.date is non-editable in the model, so it is not included
    in this ModelForm.
    """

    class Meta:
        model = Payment
        fields = [
            "amount",
            "method",
            "receivable",
            "payable",
            "notes",
        ]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "receivable": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "payable": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Payment reference or notes",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["receivable"].required = False
        self.fields["payable"].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None or amount <= 0:
            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )

        return amount

    def clean(self):
        cleaned_data = super().clean()

        receivable = cleaned_data.get(
            "receivable"
        )
        payable = cleaned_data.get(
            "payable"
        )

        if not receivable and not payable:
            raise forms.ValidationError(
                (
                    "Select either a receivable "
                    "or a payable."
                )
            )

        if receivable and payable:
            raise forms.ValidationError(
                (
                    "A payment cannot be linked to both "
                    "a receivable and a payable."
                )
            )

        return cleaned_data


class ReceivablePaymentForm(forms.ModelForm):
    """
    Payment form used on the receivable detail page.

    Payment.date is assigned automatically by the Payment model/service.
    """

    class Meta:
        model = Payment
        fields = [
            "amount",
            "method",
            "notes",
        ]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Payment reference or notes",
                }
            ),
        }

    def __init__(
        self,
        *args,
        receivable=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.receivable = receivable

        if receivable is not None:
            self.fields["amount"].widget.attrs[
                "max"
            ] = receivable.balance

            if not self.is_bound:
                self.fields["amount"].initial = (
                    receivable.balance
                )

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None or amount <= 0:
            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )

        if (
            self.receivable is not None
            and amount > self.receivable.balance
        ):
            raise forms.ValidationError(
                (
                    "Payment cannot exceed the "
                    "outstanding balance."
                )
            )

        return amount


class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = [
            "employee",
            "month",
            "basic_salary",
            "overtime_hours",
            "overtime_rate",
            "deductions",
        ]
        widgets = {
            "employee": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "month": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "basic_salary": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "overtime_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.25",
                }
            ),
            "overtime_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "deductions": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["month"].input_formats = [
            "%Y-%m-%d",
        ]

    def clean(self):
        cleaned_data = super().clean()

        for field_name in [
            "basic_salary",
            "overtime_hours",
            "overtime_rate",
            "deductions",
        ]:
            value = cleaned_data.get(
                field_name
            )

            if value is not None and value < 0:
                self.add_error(
                    field_name,
                    "This value cannot be negative.",
                )

        return cleaned_data
