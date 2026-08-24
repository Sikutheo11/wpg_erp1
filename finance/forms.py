from decimal import Decimal
from django import forms
from django.forms import formset_factory, inlineformset_factory
from django.utils import timezone
from inventory.models import Product
from .models import (
    Account,
    Counterparty,
    DebtLine,
    DebtRecord,
    Income,
    IncomeDeclaration,
    Expense,
    ExpenseRequest,
    Receivable,
    Payable,
    Payment,
    Payroll,
    ObligationLine,
    ObligationItemGroup,
    ObligationItemType,
)

from .identity import normalize_rwanda_phone
from .services.counterparty_service import (
    CounterpartyService,
)
from inventory.models import (
    Asset,
    Product,
    RawMaterial,
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

    def clean_account_number(self):
        account_number = (
            self.cleaned_data.get("account_number") or ""
        ).strip()
        if not account_number:
            return None

        duplicate = Account.objects.filter(
            account_number__iexact=account_number
        )
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError(
                "An account with this number already exists."
            )
        return account_number

    def clean_balance(self):
        balance = self.cleaned_data.get("balance")
        if balance is not None and balance < 0:
            raise forms.ValidationError(
                "Account balance cannot be negative."
            )
        return balance


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = [
            "account",
            "business_unit",
            "title",
            "income_type",
            "amount",
            "date",
            "received_from",
            "sale",
            "reference",
            "notes",
        ]
        widgets = {
            "account": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "business_unit": forms.Select(attrs={"class": "form-select"}),
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
            "received_from": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "Receipt, bank or transaction reference"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Backward compatibility for existing integrations and records that
        # predate enterprise business-unit reporting.
        self.fields["business_unit"].required = False
        self.fields["business_unit"].initial = "SHARED"

        self.fields["date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["sale"].required = False
        self.fields["sale"].label = "Related sale (optional)"
        self.fields["received_from"].required = False
        self.fields["received_from"].queryset = Counterparty.objects.filter(is_active=True).order_by("name")
        self.fields["received_from"].label = "Received from (optional)"

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None or amount <= 0:
            raise forms.ValidationError(
                "Income amount must be greater than zero."
            )

        return amount

    def clean_business_unit(self):
        return self.cleaned_data.get("business_unit") or "SHARED"


def _lock_business_unit_to_employee(form, user):
    if not user or user.is_superuser:
        return
    employee = getattr(user, "employee", None)
    department = getattr(employee, "department", None)
    if not department:
        form.fields["business_unit"].disabled = True
        form.fields["business_unit"].help_text = (
            "Ask HR to assign your employee profile to a department before saving."
        )
        return
    form.fields["business_unit"].initial = department.business_unit
    form.fields["business_unit"].disabled = True
    form.fields["business_unit"].help_text = (
        f"Assigned automatically from {department.get_name_display()}."
    )


class IncomeDeclarationForm(forms.ModelForm):
    class Meta:
        model = IncomeDeclaration
        fields = (
            "business_unit", "title", "source_type", "amount", "received_from",
            "related_sale", "receipt_method", "receipt_date", "reference",
            "proof_document", "notes",
        )
        widgets = {
            "business_unit": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "source_type": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
            "received_from": forms.Select(attrs={"class": "form-select"}),
            "related_sale": forms.Select(attrs={"class": "form-select"}),
            "receipt_method": forms.Select(attrs={"class": "form-select"}),
            "receipt_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "proof_document": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["receipt_date"].input_formats = ["%Y-%m-%d"]
        self.fields["received_from"].queryset = Counterparty.objects.filter(is_active=True).order_by("name")
        self.fields["received_from"].required = False
        self.fields["related_sale"].required = False
        self.fields["proof_document"].help_text = "Attach receipt, bank slip or Mobile Money confirmation."
        _lock_business_unit_to_employee(self, user)


class IncomeConfirmationForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.none(), widget=forms.Select(attrs={"class": "form-select"}), label="Account where funds arrived")
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.order_by("name")


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            "account",
            "business_unit",
            "title",
            "expense_type",
            "amount",
            "date",
            "paid_to",
            "reference",
            "notes",
        ]
        widgets = {
            "account": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "business_unit": forms.Select(attrs={"class": "form-select"}),
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
            "paid_to": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "Receipt, invoice or transaction reference"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Backward compatibility for existing integrations and records that
        # predate enterprise business-unit reporting.
        self.fields["business_unit"].required = False
        self.fields["business_unit"].initial = "SHARED"

        self.fields["date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["paid_to"].required = False
        self.fields["paid_to"].queryset = Counterparty.objects.filter(is_active=True).order_by("name")
        self.fields["paid_to"].label = "Paid to (optional)"

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None or amount <= 0:
            raise forms.ValidationError(
                "Expense amount must be greater than zero."
            )

        return amount

    def clean_business_unit(self):
        return self.cleaned_data.get("business_unit") or "SHARED"


class ExpenseRequestForm(forms.ModelForm):
    class Meta:
        model = ExpenseRequest
        fields = (
            "business_unit", "request_type", "title", "expense_type",
            "purpose", "payee", "amount_requested", "needed_by",
            "urgency", "supporting_document",
        )
        widgets = {
            "business_unit": forms.Select(attrs={"class": "form-select"}),
            "request_type": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "expense_type": forms.Select(attrs={"class": "form-select"}),
            "purpose": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "payee": forms.Select(attrs={"class": "form-select"}),
            "amount_requested": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
            "needed_by": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "urgency": forms.Select(attrs={"class": "form-select"}),
            "supporting_document": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["needed_by"].input_formats = ["%Y-%m-%d"]
        self.fields["payee"].queryset = Counterparty.objects.filter(is_active=True).order_by("name")
        self.fields["payee"].label = "Paid to (person or company)"
        _lock_business_unit_to_employee(self, user)

    def clean_amount_requested(self):
        amount = self.cleaned_data.get("amount_requested")
        if amount is None or amount <= 0:
            raise forms.ValidationError("Requested amount must be greater than zero.")
        return amount


class ExpenseRequestDecisionForm(forms.Form):
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))


class ExpenseRequestVerificationForm(ExpenseRequestDecisionForm):
    proposed_account = forms.ModelChoiceField(queryset=Account.objects.none(), widget=forms.Select(attrs={"class": "form-select"}))
    funds_available = forms.BooleanField(required=False, label="Funds are available")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proposed_account"].queryset = Account.objects.order_by("name")

    def clean(self):
        cleaned = super().clean()
        account = cleaned.get("proposed_account")
        if account and cleaned.get("funds_available") and account.balance <= 0:
            self.add_error("funds_available", "The selected account has no available balance.")
        return cleaned


class ExpenseRequestPaymentForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.none(), widget=forms.Select(attrs={"class": "form-select"}))
    amount = forms.DecimalField(min_value=Decimal("0.01"), decimal_places=2, max_digits=15, widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}))
    method = forms.ChoiceField(choices=ExpenseRequest.PAYMENT_METHODS, widget=forms.Select(attrs={"class": "form-select"}))
    reference = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))

    def __init__(self, *args, expense_request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.expense_request = expense_request
        self.fields["account"].queryset = Account.objects.order_by("name")
        if expense_request:
            self.fields["amount"].initial = expense_request.amount_requested
            self.fields["account"].initial = expense_request.proposed_account_id

    def clean(self):
        cleaned = super().clean()
        account, amount = cleaned.get("account"), cleaned.get("amount")
        if self.expense_request and amount and amount > self.expense_request.amount_requested:
            self.add_error("amount", "Payment cannot exceed the approved amount.")
        if account and amount and account.balance < amount:
            self.add_error("account", "The selected account does not have enough funds.")
        return cleaned


class ObligationFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["counterparty"].queryset = Counterparty.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["counterparty"].required = True
        self.fields["item_group"].required = True
        self.fields["transaction_date"].input_formats = ["%Y-%m-%d"]
        self.fields["business_unit"].choices = ObligationItemGroup.BUSINESS_UNITS
        business_unit = (
            self.data.get("business_unit")
            or self.initial.get("business_unit")
            or getattr(self.instance, "business_unit", None)
        )
        groups = ObligationItemGroup.objects.filter(is_active=True)
        if business_unit:
            groups = groups.filter(business_unit=business_unit)
        else:
            groups = groups.none()
        self.fields["item_group"].queryset = groups

    def clean(self):
        cleaned = super().clean()
        group = cleaned.get("item_group")
        business_unit = cleaned.get("business_unit")
        if group and business_unit and group.business_unit != business_unit:
            self.add_error("item_group", "Select an item group from this business unit.")
        return cleaned


class ReceivableForm(ObligationFormMixin, forms.ModelForm):
    class Meta:
        model = Receivable
        fields = [
            "counterparty",
            "business_unit",
            "item_group",
            "transaction_date",
        ]
        widgets = {
            "counterparty": forms.Select(attrs={"class": "form-select"}),
            "business_unit": forms.Select(attrs={"class": "form-select"}),
            "item_group": forms.Select(attrs={"class": "form-select"}),
            "transaction_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
        }



class PayableForm(ObligationFormMixin, forms.ModelForm):
    class Meta:
        model = Payable
        fields = [
            "counterparty",
            "business_unit",
            "item_group",
            "transaction_date",
        ]
        widgets = {
            "counterparty": forms.Select(attrs={"class": "form-select"}),
            "business_unit": forms.Select(attrs={"class": "form-select"}),
            "item_group": forms.Select(attrs={"class": "form-select"}),
            "transaction_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
        }



class ObligationLineForm(forms.ModelForm):
    class Meta:
        model = ObligationLine
        fields = ["catalog_item", "quantity", "unit_price"]
        widgets = {
            "catalog_item": forms.Select(attrs={"class": "form-select catalog-item"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "0.001", "step": "0.001"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, item_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["catalog_item"].required = True
        items = ObligationItemType.objects.filter(is_active=True)
        if item_group:
            items = items.filter(item_group=item_group)
        else:
            items = items.none()
        self.fields["catalog_item"].queryset = items
        self.fields["catalog_item"].label = "Item type"


class ObligationItemGroupForm(forms.ModelForm):
    class Meta:
        model = ObligationItemGroup
        fields = ["business_unit", "name"]
        widgets = {
            "business_unit": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Item group name"}),
        }


class ObligationItemTypeForm(forms.ModelForm):
    class Meta:
        model = ObligationItemType
        fields = ["item_group", "name", "default_unit"]
        widgets = {
            "item_group": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Item name"}),
            "default_unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "piece, kg, service..."}),
        }


class GroupAwareInlineFormSetMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        group = None
        group_id = self.data.get("item_group") if self.is_bound else getattr(self.instance, "item_group_id", None)
        if group_id:
            group = ObligationItemGroup.objects.filter(pk=group_id).first()
        for form in self.forms:
            items = ObligationItemType.objects.filter(is_active=True, item_group=group) if group else ObligationItemType.objects.none()
            form.fields["catalog_item"].queryset = items


_ReceivableLineFormSet = inlineformset_factory(
    Receivable, ObligationLine, form=ObligationLineForm, fk_name="receivable",
    extra=1, can_delete=True, min_num=1, validate_min=True,
)
_PayableLineFormSet = inlineformset_factory(
    Payable, ObligationLine, form=ObligationLineForm, fk_name="payable",
    extra=1, can_delete=True, min_num=1, validate_min=True,
)


class ReceivableLineFormSet(GroupAwareInlineFormSetMixin, _ReceivableLineFormSet):
    pass


class PayableLineFormSet(GroupAwareInlineFormSetMixin, _PayableLineFormSet):
    pass


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

class CounterpartyPhoneLookupForm(forms.Form):
    phone = forms.CharField(
        label="Telephone number",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "type": "tel",
                "placeholder": "e.g. 0788123456",
                "autocomplete": "tel",
                "autofocus": True,
                "inputmode": "tel",
            }
        ),
        help_text=(
            "Enter the telephone number first. "
            "We will check whether this person or "
            "company is already registered."
        ),
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        normalized_phone, unused_identity = (
            normalize_rwanda_phone(phone)
        )

        return normalized_phone


class CounterpartyCreateForm(forms.ModelForm):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    BOTH = "BOTH"

    RELATIONSHIP_CHOICES = (
        (
            CUSTOMER,
            "They may owe WPG money",
        ),
        (
            SUPPLIER,
            "WPG may owe them money",
        ),
        (
            BOTH,
            "Both customer and supplier",
        ),
    )

    relationship = forms.ChoiceField(
        label="Relationship with WPG",
        choices=RELATIONSHIP_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    phone = forms.CharField(
        label="Telephone number",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": True,
            }
        ),
    )

    class Meta:
        model = Counterparty
        fields = [
            "phone",
            "party_type",
            "name",
            "relationship",
            "email",
            "address",
            "tax_number",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
        ]
        widgets = {
            "party_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Person, company or institution name"
                    ),
                    "autocomplete": "name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address (optional)",
                    "autocomplete": "email",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Address (optional)",
                }
            ),
            "tax_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "TIN or tax number (optional)",
                }
            ),
            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Bank name (optional)",
                }
            ),
            "bank_account_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Name shown on the bank account"
                    ),
                }
            ),
            "bank_account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Bank account number (optional)"
                    ),
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(
        self,
        *args,
        pending_phone=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.pending_phone = pending_phone

        if pending_phone:
            self.fields["phone"].initial = pending_phone

    def clean_phone(self):
        submitted_phone = self.cleaned_data.get(
            "phone"
        )
        normalized_phone, unused_identity = (
            normalize_rwanda_phone(submitted_phone)
        )

        if self.pending_phone:
            expected_phone, unused_expected_identity = (
                normalize_rwanda_phone(
                    self.pending_phone
                )
            )

            if normalized_phone != expected_phone:
                raise forms.ValidationError(
                    (
                        "The telephone number does not match "
                        "the number that was searched."
                    )
                )

        existing = (
            CounterpartyService.find_by_phone(
                normalized_phone
            )
        )

        if existing is not None:
            raise forms.ValidationError(
                (
                    "This telephone number already belongs "
                    f"to {existing.name}. Return to telephone "
                    "search and use the existing record."
                )
            )

        return normalized_phone

    def clean_bank_account_number(self):
        bank_account_number = (
            self.cleaned_data.get(
                "bank_account_number"
            )
            or ""
        ).strip()

        if not bank_account_number:
            return ""

        existing = (
            CounterpartyService
            .find_by_bank_account(
                bank_account_number
            )
        )

        if existing is not None:
            raise forms.ValidationError(
                (
                    "This bank account already belongs "
                    f"to {existing.name}. Do not create "
                    "another record."
                )
            )

        return bank_account_number

    def clean_name(self):
        name = (
            self.cleaned_data.get("name")
            or ""
        ).strip()

        if not name:
            raise forms.ValidationError(
                "Enter the person or company name."
            )

        return name

    def clean(self):
        cleaned_data = super().clean()

        bank_account_number = (
            cleaned_data.get(
                "bank_account_number"
            )
            or ""
        ).strip()
        bank_name = (
            cleaned_data.get("bank_name")
            or ""
        ).strip()

        if bank_account_number and not bank_name:
            self.add_error(
                "bank_name",
                (
                    "Enter the bank name when an "
                    "account number is provided."
                ),
            )

        return cleaned_data


# =====================================================
# DIRECT COUNTERPARTY DEBT
# =====================================================

class DirectDebtForm(forms.Form):
    direction = forms.ChoiceField(
        label="Who owes the money?",
        choices=DebtRecord.DIRECTIONS,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    business_unit = forms.ChoiceField(
        label="Business unit",
        choices=DebtRecord.BUSINESS_UNITS,
        initial="GENERAL",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    transaction_date = forms.DateField(
        label="Transaction date",
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            },
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )

    due_date = forms.DateField(
        label="Due date",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            },
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )

    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": (
                    "Agreement, invoice number or other notes"
                ),
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        transaction_date = cleaned_data.get(
            "transaction_date"
        )
        due_date = cleaned_data.get("due_date")

        if (
            transaction_date
            and due_date
            and due_date < transaction_date
        ):
            self.add_error(
                "due_date",
                (
                    "Due date cannot be earlier than "
                    "the transaction date."
                ),
            )

        return cleaned_data


class DebtLineForm(forms.Form):
    item_type = forms.ChoiceField(
        label="Item type",
        choices=DebtLine.ITEM_TYPES,
        initial=DebtLine.PRODUCT,
        widget=forms.Select(
            attrs={
                "class": "form-select debt-item-type",
            }
        ),
    )

    product = forms.ModelChoiceField(
        label="Product",
        queryset=Product.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select debt-product",
            }
        ),
    )

    raw_material = forms.ModelChoiceField(
        label="Raw material",
        queryset=RawMaterial.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select debt-raw-material",
            }
        ),
    )

    asset = forms.ModelChoiceField(
        label="Asset",
        queryset=Asset.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select debt-asset",
            }
        ),
    )

    description = forms.CharField(
        label="Description",
        max_length=300,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control debt-description",
                "placeholder": (
                    "Describe the service or other item"
                ),
            }
        ),
    )

    quantity = forms.DecimalField(
        label="Quantity",
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
        initial=Decimal("1.000"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control debt-quantity",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )

    unit = forms.CharField(
        label="Unit",
        max_length=30,
        initial="piece",
        widget=forms.TextInput(
            attrs={
                "class": "form-control debt-unit",
                "placeholder": (
                    "piece, kg, litre, service..."
                ),
            }
        ),
    )

    unit_price = forms.DecimalField(
        label="Unit price",
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control debt-unit-price",
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["product"].queryset = (
            Product.objects.filter(
                is_active=True,
            ).order_by("name")
        )

        self.fields["raw_material"].queryset = (
            RawMaterial.objects.filter(
                status="active",
            ).order_by("name")
        )

        self.fields["asset"].queryset = (
            Asset.objects.exclude(
                status="disposed",
            ).order_by("name")
        )

    def clean(self):
        cleaned_data = super().clean()

        item_type = cleaned_data.get("item_type")
        product = cleaned_data.get("product")
        raw_material = cleaned_data.get(
            "raw_material"
        )
        asset = cleaned_data.get("asset")
        description = (
            cleaned_data.get("description")
            or ""
        ).strip()

        if item_type == DebtLine.PRODUCT:
            if not product:
                self.add_error(
                    "product",
                    "Select the product supplied.",
                )

            if raw_material or asset:
                raise forms.ValidationError(
                    (
                        "A product line cannot also contain "
                        "a raw material or asset."
                    )
                )

        elif item_type == DebtLine.RAW_MATERIAL:
            if not raw_material:
                self.add_error(
                    "raw_material",
                    "Select the raw material supplied.",
                )

            if product or asset:
                raise forms.ValidationError(
                    (
                        "A raw-material line cannot also "
                        "contain a product or asset."
                    )
                )

        elif item_type == DebtLine.ASSET:
            if not asset:
                self.add_error(
                    "asset",
                    "Select the asset involved.",
                )

            if product or raw_material:
                raise forms.ValidationError(
                    (
                        "An asset line cannot also contain "
                        "a product or raw material."
                    )
                )

        elif item_type in {
            DebtLine.SERVICE,
            DebtLine.OTHER,
        }:
            if not description:
                self.add_error(
                    "description",
                    "Describe the service or other item.",
                )

            if product or raw_material or asset:
                raise forms.ValidationError(
                    (
                        "A service or other line cannot "
                        "reference an inventory item."
                    )
                )

        return cleaned_data


DebtLineFormSet = formset_factory(
    DebtLineForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
