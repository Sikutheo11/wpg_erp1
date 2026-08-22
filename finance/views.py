from datetime import date

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from .dashboard import get_finance_dashboard

from .forms import (
    CounterpartyCreateForm,
    CounterpartyPhoneLookupForm,
    DebtLineFormSet,
    DirectDebtForm,
    PayableForm,
    ReceivablePaymentForm,
)

from .models import (
    Account,
    Counterparty,
    DebtRecord,
    Income,
    Expense,
    Receivable,
    Payable,
    Payment,
    Payroll,
    calculate_financial_summary,
)
from .services import (
    PayableService,
    PaymentService,
)

from .services.counterparty_service import (
    CounterpartyService,
)

from .services.debt_service import DebtService


# =====================================================
# COUNTERPARTY PHONE-FIRST REGISTRATION
# =====================================================

@login_required
def counterparty_phone_lookup(request):
    """
    Require a telephone lookup before an existing
    counterparty is selected or a new one is created.
    """
    if request.method == "POST":
        form = CounterpartyPhoneLookupForm(
            request.POST
        )

        if form.is_valid():
            phone = form.cleaned_data["phone"]

            counterparty = (
                CounterpartyService.find_by_phone(
                    phone
                )
            )

            if counterparty is not None:
                request.session.pop(
                    "counterparty_pending_phone",
                    None,
                )

                messages.info(
                    request,
                    (
                        f"{counterparty.name} is already "
                        "registered. Use this account for "
                        "the new transaction."
                    ),
                )

                return redirect(
                    "finance:counterparty_detail",
                    pk=counterparty.pk,
                )

            request.session[
                "counterparty_pending_phone"
            ] = phone

            return redirect(
                "finance:counterparty_create",
            )

    else:
        request.session.pop(
            "counterparty_pending_phone",
            None,
        )
        form = CounterpartyPhoneLookupForm()

    return render(
        request,
        "finance/counterparties/phone_lookup.html",
        {
            "form": form,
            "page_title": "Find Person or Company",
        },
    )


@login_required
def counterparty_create(request):
    pending_phone = request.session.get(
        "counterparty_pending_phone"
    )

    if not pending_phone:
        messages.warning(
            request,
            (
                "Search for the telephone number before "
                "creating a new person or company."
            ),
        )
        return redirect(
            "finance:counterparty_phone_lookup",
        )

    if request.method == "POST":
        form = CounterpartyCreateForm(
            request.POST,
            pending_phone=pending_phone,
        )

        if form.is_valid():
            data = form.cleaned_data
            relationship = data["relationship"]

            try:
                counterparty = (
                    CounterpartyService
                    .create_counterparty(
                        name=data["name"],
                        phone=data["phone"],
                        party_type=data[
                            "party_type"
                        ],
                        email=data.get(
                            "email",
                            "",
                        ),
                        address=data.get(
                            "address",
                            "",
                        ),
                        tax_number=data.get(
                            "tax_number",
                            "",
                        ),
                        bank_name=data.get(
                            "bank_name",
                            "",
                        ),
                        bank_account_name=data.get(
                            "bank_account_name",
                            "",
                        ),
                        bank_account_number=data.get(
                            "bank_account_number",
                            "",
                        ),
                        is_customer=(
                            relationship
                            in {
                                CounterpartyCreateForm
                                .CUSTOMER,
                                CounterpartyCreateForm
                                .BOTH,
                            }
                        ),
                        is_supplier=(
                            relationship
                            in {
                                CounterpartyCreateForm
                                .SUPPLIER,
                                CounterpartyCreateForm
                                .BOTH,
                            }
                        ),
                    )
                )

            except ValidationError as error:
                if hasattr(
                    error,
                    "message_dict",
                ):
                    for (
                        field,
                        field_messages,
                    ) in error.message_dict.items():
                        target_field = (
                            field
                            if field in form.fields
                            else None
                        )

                        for error_message in field_messages:
                            form.add_error(
                                target_field,
                                error_message,
                            )
                else:
                    for error_message in error.messages:
                        form.add_error(
                            None,
                            error_message,
                        )

            else:
                request.session.pop(
                    "counterparty_pending_phone",
                    None,
                )

                messages.success(
                    request,
                    (
                        f"{counterparty.name} was "
                        "registered successfully."
                    ),
                )

                return redirect(
                    "finance:counterparty_detail",
                    pk=counterparty.pk,
                )

    else:
        form = CounterpartyCreateForm(
            pending_phone=pending_phone,
            initial={
                "phone": pending_phone,
            },
        )

    return render(
        request,
        "finance/counterparties/counterparty_form.html",
        {
            "form": form,
            "pending_phone": pending_phone,
            "page_title": "Register Person or Company",
        },
    )


@login_required
def counterparty_detail(request, pk):
    counterparty = get_object_or_404(
        Counterparty.objects.select_related(
            "sales_customer",
            "inventory_supplier",
        ),
        pk=pk,
    )

    return render(
        request,
        "finance/counterparties/counterparty_detail.html",
        {
            "counterparty": counterparty,
            "page_title": counterparty.name,
        },
    )


@login_required
def counterparty_debt_create(
    request,
    counterparty_pk,
):
    counterparty = get_object_or_404(
        Counterparty.objects.select_related(
            "sales_customer",
            "inventory_supplier",
        ).prefetch_related(
            "debt_records__lines",
        ),
        pk=counterparty_pk,
    )

    if request.method == "POST":
        form = DirectDebtForm(request.POST)
        line_formset = DebtLineFormSet(
            request.POST,
            prefix="lines",
        )

        if form.is_valid() and line_formset.is_valid():
            lines = []

            for line_form in line_formset:
                line_data = line_form.cleaned_data

                if not line_data:
                    continue

                if line_data.get("DELETE"):
                    continue

                lines.append(
                    {
                        "item_type": line_data[
                            "item_type"
                        ],
                        "product": line_data.get(
                            "product"
                        ),
                        "raw_material": line_data.get(
                            "raw_material"
                        ),
                        "asset": line_data.get(
                            "asset"
                        ),
                        "description": line_data.get(
                            "description",
                            "",
                        ),
                        "quantity": line_data[
                            "quantity"
                        ],
                        "unit": line_data["unit"],
                        "unit_price": line_data[
                            "unit_price"
                        ],
                    }
                )

            try:
                debt = DebtService.create_debt(
                    counterparty=counterparty,
                    direction=form.cleaned_data[
                        "direction"
                    ],
                    business_unit=form.cleaned_data[
                        "business_unit"
                    ],
                    transaction_date=(
                        form.cleaned_data[
                            "transaction_date"
                        ]
                    ),
                    due_date=form.cleaned_data.get(
                        "due_date"
                    ),
                    notes=form.cleaned_data.get(
                        "notes",
                        "",
                    ),
                    lines=lines,
                    actor=request.user,
                )

            except ValidationError as error:
                if hasattr(error, "message_dict"):
                    error_messages = []

                    for field_messages in (
                        error.message_dict.values()
                    ):
                        error_messages.extend(
                            field_messages
                        )
                else:
                    error_messages = error.messages

                for error_message in error_messages:
                    form.add_error(
                        None,
                        error_message,
                    )

            else:
                messages.success(
                    request,
                    (
                        f"Debt {debt.reference} was "
                        "recorded successfully."
                    ),
                )

                return redirect(
                    "finance:counterparty_detail",
                    pk=counterparty.pk,
                )

    else:
        form = DirectDebtForm()
        line_formset = DebtLineFormSet(
            prefix="lines",
        )

    return render(
        request,
        "finance/counterparties/debt_form.html",
        {
            "counterparty": counterparty,
            "form": form,
            "line_formset": line_formset,
            "page_title": (
                f"Record Debt — {counterparty.name}"
            ),
        },
    )


# =====================================================
# PAYABLE PAYMENT FORM
# =====================================================

class PayablePaymentForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
            }
        ),
    )

    method = forms.ChoiceField(
        choices=Payment.METHODS,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Payment reference or notes",
            }
        ),
    )

    def __init__(
        self,
        *args,
        payable=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.payable = payable

        self.fields["account"].queryset = (
            Account.objects.all().order_by(
                "name",
            )
        )

        if payable is not None:
            self.fields["amount"].widget.attrs[
                "max"
            ] = payable.balance

            if not self.is_bound:
                self.fields["amount"].initial = (
                    payable.balance
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
            self.payable is not None
            and amount > self.payable.balance
        ):
            raise forms.ValidationError(
                (
                    "Payment cannot exceed the "
                    "outstanding balance."
                )
            )

        return amount


# =====================================================
# COMMON HELPERS
# =====================================================

def _validation_message(error):
    if hasattr(error, "messages"):
        return "; ".join(error.messages)

    return str(error)


def _parse_date(value, default):
    if not value:
        return default

    try:
        return date.fromisoformat(value)

    except ValueError:
        return default


# =====================================================
# FINANCE DASHBOARD
# =====================================================

@login_required
def finance_dashboard(request):
    context = get_finance_dashboard(
        request.user
    )

    return render(
        request,
        "finance/dashboard.html",
        context,
    )


# =====================================================
# ACCOUNT
# =====================================================

@login_required
def account_list(request):
    accounts = Account.objects.all().order_by(
        "account_number",
        "name",
    )

    return render(
        request,
        "finance/accounts/account_list.html",
        {
            "accounts": accounts,
        },
    )


# =====================================================
# INCOME
# =====================================================

@login_required
def income_list(request):
    incomes = (
        Income.objects
        .select_related(
            "account",
            "sale",
        )
        .order_by(
            "-date",
            "-created_at",
        )
    )

    return render(
        request,
        "finance/income/income_list.html",
        {
            "incomes": incomes,
        },
    )


# =====================================================
# EXPENSE
# =====================================================

@login_required
def expense_list(request):
    expenses = (
        Expense.objects
        .select_related(
            "account",
            "supplier",
        )
        .order_by(
            "-date",
            "-created_at",
        )
    )

    return render(
        request,
        "finance/expense/expense_list.html",
        {
            "expenses": expenses,
        },
    )


# =====================================================
# RECEIVABLE LIST
# =====================================================

@login_required
def receivable_list(request):
    base_queryset = (
        Receivable.objects
        .select_related(
            "order",
            "customer",
        )
        .order_by(
            "-created_at",
        )
    )

    search = (
        request.GET.get(
            "q",
            "",
        )
        .strip()
    )

    status = (
        request.GET.get(
            "status",
            "",
        )
        .strip()
        .lower()
    )

    receivables = base_queryset

    if search:
        receivables = receivables.filter(
            Q(invoice_number__icontains=search)
            | Q(order__order_number__icontains=search)
            | Q(order__customer_name__icontains=search)
            | Q(order__customer_phone__icontains=search)
            | Q(customer__username__icontains=search)
            | Q(customer__email__icontains=search)
        )

    valid_statuses = {
        value
        for value, label in Receivable.STATUS
    }

    if status in valid_statuses:
        receivables = receivables.filter(
            status=status
        )

    return render(
        request,
        "finance/receivables/receivable_list.html",
        {
            "receivables": receivables,
            "search": search,
            "selected_status": status,
            "status_choices": Receivable.STATUS,
            "total_count": base_queryset.count(),
            "unpaid_count": base_queryset.filter(
                status="unpaid"
            ).count(),
            "partial_count": base_queryset.filter(
                status="partial"
            ).count(),
            "overdue_count": base_queryset.filter(
                status="overdue"
            ).count(),
        },
    )


# =====================================================
# RECEIVABLE DETAIL
# =====================================================

@login_required
def receivable_detail(request, pk):
    receivable = get_object_or_404(
        Receivable.objects.select_related(
            "order",
            "customer",
        ).prefetch_related(
            "payment_set",
        ),
        pk=pk,
    )

    payments = (
        receivable.payment_set
        .all()
        .order_by(
            "-date",
            "-pk",
        )
    )

    payment_form = ReceivablePaymentForm(
        receivable=receivable,
    )

    return render(
        request,
        "finance/receivables/receivable_detail.html",
        {
            "receivable": receivable,
            "payments": payments,
            "payment_form": payment_form,
            "can_record_payment": (
                receivable.status != "paid"
                and receivable.balance > 0
            ),
        },
    )


# =====================================================
# RECORD RECEIVABLE PAYMENT
# =====================================================

@login_required
def record_receivable_payment(request, pk):
    receivable = get_object_or_404(
        Receivable.objects.select_related(
            "order",
            "customer",
        ),
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "finance:debt_list",
        )

    form = ReceivablePaymentForm(
        request.POST,
        receivable=receivable,
    )

    if form.is_valid():
        data = form.cleaned_data

        try:
            payment = (
                PaymentService
                .record_receivable_payment(
                    receivable=receivable,
                    amount=data["amount"],
                    method=data["method"],
                    notes=data.get(
                        "notes",
                        "",
                    ),
                    actor=request.user,
                )
            )

        except ValidationError as error:
            form.add_error(
                None,
                _validation_message(error),
            )

        else:
            messages.success(
                request,
                (
                    f"Payment of {payment.amount} RWF "
                    "recorded successfully."
                ),
            )

            return redirect(
                "finance:receivable_detail",
                pk=receivable.pk,
            )

    payments = (
        receivable.payment_set
        .all()
        .order_by(
            "-date",
            "-pk",
        )
    )

    return render(
        request,
        "finance/receivables/receivable_detail.html",
        {
            "receivable": receivable,
            "payments": payments,
            "payment_form": form,
            "can_record_payment": (
                receivable.status != "paid"
                and receivable.balance > 0
            ),
        },
    )


# =====================================================
# PAYABLE LIST
# =====================================================

@login_required
def payable_list(request):
    base_queryset = (
        Payable.objects
        .select_related(
            "supplier",
        )
        .order_by(
            "-created_at",
        )
    )

    search = (
        request.GET.get(
            "q",
            "",
        )
        .strip()
    )

    payables = base_queryset

    if search:
        payables = payables.filter(
            Q(reference__icontains=search)
            | Q(supplier__name__icontains=search)
        )

    outstanding_total = (
        payables.aggregate(
            total=Sum(
                F("total_amount")
                - F("amount_paid")
            )
        )["total"]
        or 0
    )

    paid_total = (
        payables.aggregate(
            total=Sum("amount_paid")
        )["total"]
        or 0
    )

    return render(
        request,
        "finance/payables/payable_list.html",
        {
            "payables": payables,
            "search": search,
            "total_count": payables.count(),
            "outstanding_total": outstanding_total,
            "paid_total": paid_total,
            "overdue_count": payables.filter(
                status="overdue"
            ).count(),
        },
    )


# =====================================================
# CREATE PAYABLE
# =====================================================

@login_required
def payable_create(request):
    if request.method == "POST":
        form = PayableForm(
            request.POST
        )

        if form.is_valid():
            data = form.cleaned_data

            try:
                payable = (
                    PayableService.create_payable(
                        supplier=data["supplier"],
                        reference=data["reference"],
                        total_amount=data[
                            "total_amount"
                        ],
                        due_date=data["due_date"],
                        actor=request.user,
                    )
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    _validation_message(error),
                )

            else:
                messages.success(
                    request,
                    (
                        f"Payable {payable.reference} "
                        "created successfully."
                    ),
                )

                return redirect(
                    "finance:payable_detail",
                    pk=payable.pk,
                )

    else:
        form = PayableForm()

    return render(
        request,
        "finance/payables/payable_form.html",
        {
            "form": form,
            "page_title": "Create Payable",
        },
    )


# =====================================================
# PAYABLE DETAIL
# =====================================================

@login_required
def payable_detail(request, pk):
    payable = get_object_or_404(
        Payable.objects.select_related(
            "supplier",
        ),
        pk=pk,
    )

    payments = (
        Payment.objects
        .filter(
            payable=payable,
        )
        .order_by(
            "-date",
            "-pk",
        )
    )

    return render(
        request,
        "finance/payables/payable_detail.html",
        {
            "payable": payable,
            "payments": payments,
        },
    )


# =====================================================
# PAYABLE PAYMENT
# =====================================================

@login_required
def payable_payment(request, pk):
    payable = get_object_or_404(
        Payable.objects.select_related(
            "supplier",
        ),
        pk=pk,
    )

    if (
        payable.status == "paid"
        or payable.balance <= 0
    ):
        messages.info(
            request,
            "This payable has already been fully paid.",
        )

        return redirect(
            "finance:payable_detail",
            pk=payable.pk,
        )

    if request.method == "POST":
        form = PayablePaymentForm(
            request.POST,
            payable=payable,
        )

        if form.is_valid():
            data = form.cleaned_data

            try:
                result = PayableService.record_payment(
                    payable=payable,
                    account=data["account"],
                    amount=data["amount"],
                    method=data["method"],
                    notes=data.get(
                        "notes",
                        "",
                    ),
                    actor=request.user,
                )

            except ValidationError as error:
                form.add_error(
                    None,
                    _validation_message(error),
                )

            else:
                messages.success(
                    request,
                    (
                        f"Supplier payment of "
                        f"{result['payment'].amount} RWF "
                        "recorded successfully."
                    ),
                )

                return redirect(
                    "finance:payable_detail",
                    pk=payable.pk,
                )

    else:
        form = PayablePaymentForm(
            payable=payable,
        )

    return render(
        request,
        "finance/payables/payable_payment.html",
        {
            "payable": payable,
            "form": form,
        },
    )


# =====================================================
# PAYMENT LIST
# =====================================================

@login_required
def payment_list(request):
    payments = (
        Payment.objects
        .select_related(
            "receivable",
            "receivable__order",
            "payable",
            "payable__supplier",
        )
        .order_by(
            "-date",
            "-pk",
        )
    )

    receivable_payments = payments.filter(
        receivable__isnull=False,
    )

    payable_payments = payments.filter(
        payable__isnull=False,
    )

    return render(
        request,
        "finance/payments/payment_list.html",
        {
            "payments": payments,
            "payment_count": payments.count(),
            "receivable_payment_count": (
                receivable_payments.count()
            ),
            "payable_payment_count": (
                payable_payments.count()
            ),
            "total_amount": (
                payments.aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            ),
            "customer_amount": (
                receivable_payments.aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            ),
            "supplier_amount": (
                payable_payments.aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            ),
        },
    )


# =====================================================
# PAYROLL
# =====================================================

@login_required
def payroll_list(request):
    payrolls = (
        Payroll.objects
        .select_related(
            "employee",
        )
        .order_by(
            "-month",
            "-created_at",
        )
    )

    return render(
        request,
        "finance/payroll/payroll_list.html",
        {
            "payrolls": payrolls,
        },
    )


# =====================================================
# FINANCIAL REPORT
# =====================================================

@login_required
def financial_report(request):
    today = timezone.localdate()

    default_start_date = today.replace(
        day=1
    )

    start_date = _parse_date(
        request.GET.get("start"),
        default_start_date,
    )

    end_date = _parse_date(
        request.GET.get("end"),
        today,
    )

    if start_date > end_date:
        messages.warning(
            request,
            (
                "Start date cannot be after end date. "
                "The current month has been selected."
            ),
        )

        start_date = default_start_date
        end_date = today

    summary = calculate_financial_summary(
        start_date,
        end_date,
    )

    return render(
        request,
        "finance/reports/financial_report.html",
        {
            "summary": summary,
            "start_date": start_date,
            "end_date": end_date,
        },
    )

@login_required
def debt_list(request):
    debts = (
        DebtRecord.objects
        .select_related(
            "counterparty",
            "created_by",
        )
        .prefetch_related("lines")
        .order_by(
            "-transaction_date",
            "-pk",
        )
    )

    search = request.GET.get("q", "").strip()
    direction = (
        request.GET.get("direction", "")
        .strip()
        .upper()
    )
    status = (
        request.GET.get("status", "")
        .strip()
        .upper()
    )

    if search:
        debts = debts.filter(
            Q(reference__icontains=search)
            | Q(counterparty__name__icontains=search)
            | Q(counterparty__phone__icontains=search)
            | Q(lines__description__icontains=search)
        ).distinct()

    valid_directions = {
        value
        for value, unused_label
        in DebtRecord.DIRECTIONS
    }

    if direction in valid_directions:
        debts = debts.filter(direction=direction)
    else:
        direction = ""

    valid_statuses = {
        value
        for value, unused_label
        in DebtRecord.STATUSES
    }

    if status in valid_statuses:
        debts = debts.filter(status=status)
    else:
        status = ""

    summary = debts.aggregate(
        total_debt=Sum("total_amount"),
        total_paid=Sum("amount_paid"),
    )

    total_debt = summary["total_debt"] or 0
    total_paid = summary["total_paid"] or 0

    return render(
        request,
        "finance/counterparties/debt_list.html",
        {
            "debts": debts,
            "search": search,
            "selected_direction": direction,
            "selected_status": status,
            "direction_choices": DebtRecord.DIRECTIONS,
            "status_choices": DebtRecord.STATUSES,
            "total_debt": total_debt,
            "total_paid": total_paid,
            "total_balance": (
                total_debt - total_paid
            ),
            "page_title": "Debts",
        },
    )
