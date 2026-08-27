from datetime import date
import csv
from io import BytesIO
from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.db.models import F, Q, Sum
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.permissions import wpg_permission_required

from .dashboard import get_finance_dashboard

from .forms import (
    AccountForm,
    ExpenseForm,
    ExpenseRequestForm,
    ExpenseRequestDecisionForm,
    ExpenseRequestVerificationForm,
    ExpenseRequestPaymentForm,
    IncomeForm,
    IncomeDeclarationForm,
    IncomeConfirmationForm,
    CounterpartyCreateForm,
    CounterpartyPhoneLookupForm,
    PayableForm,
    PayableLineFormSet,
    ReceivableForm,
    ReceivableLineFormSet,
    ReceivablePaymentForm,
    ObligationItemGroupForm,
    ObligationItemTypeForm,
)

from .models import (
    Account,
    Counterparty,
    DebtRecord,
    Income,
    IncomeDeclaration,
    Expense,
    ExpenseRequest,
    Receivable,
    Payable,
    Payment,
    Payroll,
    calculate_financial_summary,
    ObligationItemGroup,
    ObligationItemType,
)
from .services import (
    PayableService,
    PaymentService,
    ObligationService,
    DebtReportService,
)

from .services.counterparty_service import (
    CounterpartyService,
)
from .services.expense_request_service import ExpenseRequestService
from .services.income_declaration_service import IncomeDeclarationService
from .services.expense_service import ExpenseService
from .services.income_service import IncomeService



# =====================================================
# COUNTERPARTY PHONE-FIRST REGISTRATION
# =====================================================

@login_required
@wpg_permission_required(
    "finance.view_counterparty",
    feature_code="FINANCE_COUNTERPARTIES",
)
def counterparty_phone_lookup(request):
    """
    Require a telephone lookup before an existing
    counterparty is selected or a new one is created.
    """
    return_target = request.GET.get("next") or request.POST.get("next")
    if return_target in {"payable", "receivable"}:
        request.session["counterparty_return_target"] = return_target
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

                target = request.session.pop("counterparty_return_target", None)
                if target:
                    return redirect(f"/finance/{target}s/create/?counterparty={counterparty.pk}")
                return redirect("finance:counterparty_detail", pk=counterparty.pk)

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
@wpg_permission_required(
    "finance.add_counterparty",
    feature_code="FINANCE_COUNTERPARTIES",
    action="add",
)
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

                target = request.session.pop("counterparty_return_target", None)
                if target:
                    return redirect(f"/finance/{target}s/create/?counterparty={counterparty.pk}")
                return redirect("finance:counterparty_detail", pk=counterparty.pk)

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
@wpg_permission_required(
    "finance.view_counterparty",
    feature_code="FINANCE_COUNTERPARTIES",
)
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
@wpg_permission_required(
    "finance.add_debtrecord",
    feature_code="FINANCE_DEBTS",
    action="add",
)
def counterparty_debt_create(
    request,
    counterparty_pk,
):
    counterparty = get_object_or_404(Counterparty, pk=counterparty_pk)
    return render(request, "finance/counterparties/obligation_choice.html", {
        "counterparty": counterparty, "page_title": "Choose Debt Type",
    })


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
@wpg_permission_required(
    "finance.view_account",
    feature_code="FINANCE_DASHBOARD",
)
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
@wpg_permission_required(
    "finance.view_account",
    feature_code="FINANCE_ACCOUNTS",
)
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


@login_required
@wpg_permission_required(
    "finance.add_account",
    feature_code="FINANCE_ACCOUNTS",
    action="add",
)
def account_create(request):
    form = AccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = form.save()
        messages.success(
            request,
            f"Account {account.name} was created successfully.",
        )
        return redirect("finance:account_list")
    return render(
        request,
        "finance/accounts/account_form.html",
        {"form": form, "page_title": "Add Account"},
    )


@login_required
@wpg_permission_required(
    "finance.change_account",
    feature_code="FINANCE_ACCOUNTS",
    action="change",
)
def account_update(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = AccountForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        account = form.save()
        messages.success(
            request,
            f"Account {account.name} was updated successfully.",
        )
        return redirect("finance:account_list")
    return render(
        request,
        "finance/accounts/account_form.html",
        {
            "form": form,
            "account": account,
            "page_title": "Edit Account",
        },
    )


@login_required
@wpg_permission_required(
    "finance.delete_account",
    feature_code="FINANCE_ACCOUNTS",
    action="delete",
)
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        name = account.name
        try:
            account.delete()
        except ProtectedError:
            messages.error(
                request,
                "This account has financial records and cannot be deleted.",
            )
        else:
            messages.success(
                request,
                f"Account {name} was deleted successfully.",
            )
        return redirect("finance:account_list")
    return render(
        request,
        "finance/accounts/account_confirm_delete.html",
        {"account": account, "page_title": "Delete Account"},
    )

# =====================================================
# INCOME
# =====================================================

CENTRAL_FINANCE_GROUPS = {"Accountant", "Finance Manager", "CEO"}


def _finance_groups(user):
    return set(user.groups.values_list("name", flat=True))


def _has_central_finance_scope(user):
    return user.is_superuser or bool(_finance_groups(user) & CENTRAL_FINANCE_GROUPS)


def _employee_department(user):
    employee = getattr(user, "employee", None)
    return getattr(employee, "department", None)


def _can_access_unit_record(user, owner_id, department):
    return (
        _has_central_finance_scope(user)
        or owner_id == user.id
        or bool(department and department.manager_id == user.id)
    )


def _protected_file_response(field_file):
    if not field_file or not field_file.name:
        raise Http404("Document not found.")
    try:
        stream = field_file.storage.open(field_file.name, "rb")
    except (FileNotFoundError, OSError):
        raise Http404("Document not found.")
    return FileResponse(
        stream,
        as_attachment=True,
        filename=Path(field_file.name).name,
    )

@login_required
@wpg_permission_required("finance.view_incomedeclaration", feature_code="FINANCE_INCOME_DECLARATIONS")
def income_declaration_list(request):
    declarations = IncomeDeclaration.objects.select_related(
        "recorded_by", "department", "received_from", "related_sale",
        "confirmed_account", "unit_approved_by", "finance_confirmed_by",
    )
    if not _has_central_finance_scope(request.user):
        declarations = declarations.filter(
            Q(recorded_by=request.user) | Q(department__manager=request.user)
        ).distinct()
    business_unit = request.GET.get("business_unit", "").strip()
    if business_unit:
        declarations = declarations.filter(business_unit=business_unit)
    return render(request, "finance/income_declarations/declaration_list.html", {
        "declarations": declarations,
        "business_units": IncomeDeclaration.BUSINESS_UNITS,
        "selected_business_unit": business_unit,
    })


@login_required
@wpg_permission_required("finance.add_incomedeclaration", feature_code="FINANCE_INCOME_DECLARATIONS", action="add")
def income_declaration_create(request):
    department = _employee_department(request.user)
    form = IncomeDeclarationForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        if not department and not request.user.is_superuser:
            form.add_error(None, "Your employee profile must belong to a department before recording unit income.")
            return render(request, "finance/income_declarations/declaration_form.html", {"form": form})
        declaration = form.save(commit=False)
        declaration.recorded_by = request.user
        declaration.department = department
        if department and not request.user.is_superuser:
            declaration.business_unit = department.business_unit
        declaration.save()
        messages.success(request, "Income declaration saved as a draft.")
        return redirect("finance:income_declaration_detail", pk=declaration.pk)
    return render(request, "finance/income_declarations/declaration_form.html", {"form": form})


@login_required
@wpg_permission_required("finance.add_incomedeclaration", feature_code="FINANCE_INCOME_DECLARATIONS", action="add")
def income_declaration_update(request, pk):
    declaration = get_object_or_404(IncomeDeclaration, pk=pk, recorded_by=request.user)
    if declaration.status not in {"DRAFT", "RETURNED"}:
        messages.error(request, "Only a draft or returned declaration can be edited.")
        return redirect("finance:income_declaration_detail", pk=pk)
    form = IncomeDeclarationForm(request.POST or None, request.FILES or None, instance=declaration, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Income declaration updated.")
        return redirect("finance:income_declaration_detail", pk=pk)
    return render(request, "finance/income_declarations/declaration_form.html", {"form": form, "declaration": declaration})


@login_required
@wpg_permission_required("finance.view_incomedeclaration", feature_code="FINANCE_INCOME_DECLARATIONS")
def income_declaration_detail(request, pk):
    declaration = get_object_or_404(IncomeDeclaration.objects.select_related(
        "recorded_by", "department", "department__manager", "received_from",
        "related_sale", "unit_approved_by", "finance_confirmed_by",
        "confirmed_account", "posted_income",
    ), pk=pk)
    if not _can_access_unit_record(request.user, declaration.recorded_by_id, declaration.department):
        raise PermissionDenied
    groups = _finance_groups(request.user)
    is_recorder = declaration.recorded_by_id == request.user.id
    assigned_manager = bool(
        declaration.department_id
        and declaration.department.manager_id == request.user.id
    )
    return render(request, "finance/income_declarations/declaration_detail.html", {
        "declaration": declaration,
        "decision_form": ExpenseRequestDecisionForm(),
        "confirmation_form": IncomeConfirmationForm(),
        "can_unit_approve": request.user.is_superuser or (
            not is_recorder
            and assigned_manager
            and bool(groups & {"Manager", "Construction Manager", "Furniture Manager", "Marketplace Manager", "Finance Manager"})
        ),
        "can_finance_confirm": request.user.is_superuser or (
            not is_recorder and bool(groups & {"Accountant", "Finance Manager"})
        ),
    })


@login_required
@wpg_permission_required(
    "finance.view_incomedeclaration",
    feature_code="FINANCE_INCOME_DECLARATIONS",
)
def income_declaration_document(request, pk):
    declaration = get_object_or_404(
        IncomeDeclaration.objects.select_related("department"),
        pk=pk,
    )
    if not _can_access_unit_record(
        request.user,
        declaration.recorded_by_id,
        declaration.department,
    ):
        raise PermissionDenied
    return _protected_file_response(declaration.proof_document)


@login_required
@wpg_permission_required("finance.add_incomedeclaration", feature_code="FINANCE_INCOME_DECLARATIONS", action="add")
@require_POST
def income_declaration_submit(request, pk):
    obj = get_object_or_404(IncomeDeclaration, pk=pk)
    return _run_workflow_action(request, obj, lambda: IncomeDeclarationService.submit(obj, request.user), "Income declaration submitted to the unit manager.", "finance:income_declaration_detail")


@login_required
@wpg_permission_required("finance.change_incomedeclaration", feature_code="FINANCE_INCOME_CONFIRMATIONS", action="approve")
@require_POST
def income_declaration_unit_approve(request, pk):
    obj = get_object_or_404(IncomeDeclaration, pk=pk)
    return _run_workflow_action(request, obj, lambda: IncomeDeclarationService.unit_approve(obj, request.user, request.POST.get("comment")), "Unit manager approved the income source.", "finance:income_declaration_detail")


@login_required
@wpg_permission_required("finance.change_incomedeclaration", feature_code="FINANCE_INCOME_CONFIRMATIONS", action="approve")
@require_POST
def income_declaration_confirm(request, pk):
    obj = get_object_or_404(IncomeDeclaration, pk=pk)
    form = IncomeConfirmationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return _run_workflow_action(request, obj, lambda: IncomeDeclarationService.finance_confirm(obj, request.user, form.cleaned_data["account"], form.cleaned_data["comment"]), "Finance confirmed receipt and posted the income.", "finance:income_declaration_detail")
    messages.error(request, "; ".join(str(error) for errors in form.errors.values() for error in errors))
    return redirect("finance:income_declaration_detail", pk=obj.pk)


@login_required
@wpg_permission_required("finance.change_incomedeclaration", feature_code="FINANCE_INCOME_CONFIRMATIONS", action="approve")
@require_POST
def income_declaration_decide(request, pk, decision):
    obj = get_object_or_404(IncomeDeclaration, pk=pk)
    return _run_workflow_action(request, obj, lambda: IncomeDeclarationService.return_or_reject(obj, request.user, decision.upper(), request.POST.get("comment")), f"Income declaration {decision.lower()}.", "finance:income_declaration_detail")

@login_required
@wpg_permission_required(
    "finance.view_income",
    feature_code="FINANCE_INCOME",
)
def income_list(request):
    incomes = (
        Income.objects
        .select_related(
            "account",
            "sale",
            "received_from",
        )
        .order_by(
            "-date",
            "-created_at",
        )
    )

    return render(
        request,
        "finance/incomes/income_list.html",
        {
            "incomes": incomes,
        },
    )


@login_required
@wpg_permission_required(
    "finance.add_income",
    feature_code="FINANCE_INCOME",
    action="add",
)
def income_create(request):
    form = IncomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            result = IncomeService.create_income(
                account=data["account"],
                business_unit=data.get("business_unit") or "SHARED",
                title=data["title"],
                income_type=data["income_type"],
                amount=data["amount"],
                income_date=data["date"],
                sale=data.get("sale"),
                received_from=data.get("received_from"),
                reference=data.get("reference", ""),
                notes=data.get("notes", ""),
                actor=request.user,
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(
                request,
                f"Income {result['income']} was recorded successfully.",
            )
            return redirect("finance:income_list")
    return render(
        request,
        "finance/incomes/income_form.html",
        {"form": form, "page_title": "Add Income"},
    )


# =====================================================
# EXPENSE
# =====================================================

@login_required
@wpg_permission_required(
    "finance.view_expense",
    feature_code="FINANCE_EXPENSES",
)
def expense_list(request):
    expenses = (
        Expense.objects
        .select_related(
            "account",
            "supplier",
            "paid_to",
        )
        .order_by(
            "-date",
            "-created_at",
        )
    )

    return render(
        request,
        "finance/expenses/expense_list.html",
        {
            "expenses": expenses,
        },
    )


@login_required
@wpg_permission_required(
    "finance.add_expense",
    feature_code="FINANCE_EXPENSES",
    action="add",
)
def expense_create(request):
    form = ExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            result = ExpenseService.create_expense(
                account=data["account"],
                business_unit=data.get("business_unit") or "SHARED",
                title=data["title"],
                expense_type=data["expense_type"],
                amount=data["amount"],
                expense_date=data["date"],
                paid_to=data.get("paid_to"),
                reference=data.get("reference", ""),
                notes=data.get("notes", ""),
                actor=request.user,
            )
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(
                request,
                f"Expense {result['expense']} was recorded successfully.",
            )
            return redirect("finance:expense_list")
    return render(
        request,
        "finance/expenses/expense_form.html",
        {"form": form, "page_title": "Add Expense"},
    )


# =====================================================
# EXPENSE REQUEST APPROVAL WORKFLOW
# =====================================================

@login_required
@wpg_permission_required("finance.view_expenserequest", feature_code="FINANCE_EXPENSE_REQUESTS")
def expense_request_list(request):
    requests = ExpenseRequest.objects.select_related(
        "requested_by", "department", "payee", "proposed_account"
    )
    status = request.GET.get("status", "").strip()
    if status:
        requests = requests.filter(status=status)
    business_unit = request.GET.get("business_unit", "").strip()
    if business_unit:
        requests = requests.filter(business_unit=business_unit)
    if not _has_central_finance_scope(request.user):
        requests = requests.filter(
            Q(requested_by=request.user) | Q(department__manager=request.user)
        ).distinct()
    return render(request, "finance/expense_requests/request_list.html", {
        "expense_requests": requests,
        "status_choices": ExpenseRequest.STATUS_CHOICES,
        "selected_status": status,
        "business_units": ExpenseRequest.BUSINESS_UNITS,
        "selected_business_unit": business_unit,
    })


@login_required
@wpg_permission_required("finance.add_expenserequest", feature_code="FINANCE_EXPENSE_REQUESTS", action="add")
def expense_request_create(request):
    department = _employee_department(request.user)
    form = ExpenseRequestForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        if not department and not request.user.is_superuser:
            form.add_error(None, "Your employee profile must belong to a department before requesting money.")
            return render(request, "finance/expense_requests/request_form.html", {"form": form})
        expense_request = form.save(commit=False)
        expense_request.requested_by = request.user
        expense_request.department = department
        if department and not request.user.is_superuser:
            expense_request.business_unit = department.business_unit
        expense_request.save()
        messages.success(request, "Expense request saved as a draft.")
        return redirect("finance:expense_request_detail", pk=expense_request.pk)
    return render(request, "finance/expense_requests/request_form.html", {"form": form})


@login_required
@wpg_permission_required("finance.add_expenserequest", feature_code="FINANCE_EXPENSE_REQUESTS", action="add")
def expense_request_update(request, pk):
    expense_request = get_object_or_404(ExpenseRequest, pk=pk, requested_by=request.user)
    if expense_request.status not in {"DRAFT", "RETURNED"}:
        messages.error(request, "Only a draft or returned request can be edited.")
        return redirect("finance:expense_request_detail", pk=pk)
    form = ExpenseRequestForm(request.POST or None, request.FILES or None, instance=expense_request, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expense request updated.")
        return redirect("finance:expense_request_detail", pk=pk)
    return render(request, "finance/expense_requests/request_form.html", {"form": form, "expense_request": expense_request})


@login_required
@wpg_permission_required("finance.view_expenserequest", feature_code="FINANCE_EXPENSE_REQUESTS")
def expense_request_detail(request, pk):
    expense_request = get_object_or_404(
        ExpenseRequest.objects.select_related(
            "requested_by", "department", "department__manager", "payee",
            "proposed_account", "manager_approved_by", "accountant_verified_by",
            "finance_approved_by", "director_approved_by", "paid_by", "expense",
        ), pk=pk,
    )
    if not _can_access_unit_record(request.user, expense_request.requested_by_id, expense_request.department):
        raise PermissionDenied
    groups = set(request.user.groups.values_list("name", flat=True))
    is_superuser = request.user.is_superuser
    is_requester = expense_request.requested_by_id == request.user.id
    has_manager_role = bool(
        groups & {"Manager", "Construction Manager", "Furniture Manager", "Finance Manager"}
    )
    is_assigned_line_manager = (
        not expense_request.department_id
        or not expense_request.department.manager_id
        or expense_request.department.manager_id == request.user.id
    )
    can_manager_approve = is_superuser or (
        not is_requester and has_manager_role and is_assigned_line_manager
    )
    can_verify = is_superuser or (not is_requester and "Accountant" in groups)
    can_finance_approve = is_superuser or (not is_requester and "Finance Manager" in groups)
    can_director_approve = is_superuser or (not is_requester and "CEO" in groups)
    can_pay = is_superuser or (not is_requester and "Accountant" in groups)
    return render(request, "finance/expense_requests/request_detail.html", {
        "expense_request": expense_request,
        "decision_form": ExpenseRequestDecisionForm(),
        "verification_form": ExpenseRequestVerificationForm(initial={"proposed_account": expense_request.proposed_account_id}),
        "payment_form": ExpenseRequestPaymentForm(expense_request=expense_request),
        "can_manager_approve": can_manager_approve,
        "can_verify": can_verify,
        "can_finance_approve": can_finance_approve,
        "can_director_approve": can_director_approve,
        "can_pay": can_pay,
        "can_decide": (
            (expense_request.status == "SUBMITTED" and can_manager_approve)
            or (expense_request.status == "MANAGER_APPROVED" and can_verify)
            or (expense_request.status == "FINANCE_VERIFIED" and can_finance_approve)
            or (expense_request.status == "FINANCE_APPROVED" and can_director_approve)
            or (expense_request.status == "FINAL_APPROVED" and can_pay)
        ),
    })


@login_required
@wpg_permission_required(
    "finance.view_expenserequest",
    feature_code="FINANCE_EXPENSE_REQUESTS",
)
def expense_request_document(request, pk, kind):
    expense_request = get_object_or_404(
        ExpenseRequest.objects.select_related("department"),
        pk=pk,
    )
    if not _can_access_unit_record(
        request.user,
        expense_request.requested_by_id,
        expense_request.department,
    ):
        raise PermissionDenied
    fields = {
        "supporting": expense_request.supporting_document,
        "accountability": expense_request.accountability_document,
    }
    if kind not in fields:
        raise Http404("Unknown document type.")
    return _protected_file_response(fields[kind])


def _run_workflow_action(
    request,
    workflow_record,
    action,
    success_message,
    detail_url_name="finance:expense_request_detail",
):
    if request.method != "POST":
        return redirect(detail_url_name, pk=workflow_record.pk)
    try:
        action()
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc))
    else:
        messages.success(request, success_message)
    return redirect(detail_url_name, pk=workflow_record.pk)


@login_required
@wpg_permission_required("finance.add_expenserequest", feature_code="FINANCE_EXPENSE_REQUESTS", action="add")
@require_POST
def expense_request_submit(request, pk):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    return _run_workflow_action(request, obj, lambda: ExpenseRequestService.submit(obj, request.user), "Request submitted to the line manager.")


@login_required
@wpg_permission_required("finance.change_expenserequest", feature_code="FINANCE_EXPENSE_APPROVALS", action="approve")
@require_POST
def expense_request_manager_approve(request, pk):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    return _run_workflow_action(request, obj, lambda: ExpenseRequestService.manager_approve(obj, request.user, request.POST.get("comment")), "Line manager approved the request.")


@login_required
@wpg_permission_required("finance.change_expenserequest", feature_code="FINANCE_EXPENSE_APPROVALS", action="approve")
@require_POST
def expense_request_verify(request, pk):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    form = ExpenseRequestVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return _run_workflow_action(request, obj, lambda: ExpenseRequestService.accountant_verify(obj, request.user, form.cleaned_data["proposed_account"], form.cleaned_data["funds_available"], form.cleaned_data["comment"]), "Accountant verified funds and documents.")
    messages.error(request, "; ".join(str(error) for errors in form.errors.values() for error in errors))
    return redirect("finance:expense_request_detail", pk=obj.pk)


@login_required
@wpg_permission_required("finance.change_expenserequest", feature_code="FINANCE_EXPENSE_APPROVALS", action="approve")
@require_POST
def expense_request_finance_approve(request, pk):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    return _run_workflow_action(request, obj, lambda: ExpenseRequestService.finance_approve(obj, request.user, request.POST.get("comment")), "Finance manager approved the request.")


@login_required
@wpg_permission_required("finance.change_expenserequest", feature_code="FINANCE_EXPENSE_APPROVALS", action="approve")
@require_POST
def expense_request_director_approve(request, pk):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    return _run_workflow_action(request, obj, lambda: ExpenseRequestService.director_approve(obj, request.user, request.POST.get("comment")), "Company director gave final approval.")


@login_required
@wpg_permission_required("finance.change_expenserequest", feature_code="FINANCE_EXPENSE_APPROVALS", action="approve")
@require_POST
def expense_request_pay(request, pk):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    form = ExpenseRequestPaymentForm(request.POST or None, expense_request=obj)
    if request.method == "POST" and form.is_valid():
        return _run_workflow_action(request, obj, lambda: ExpenseRequestService.pay(obj, request.user, form.cleaned_data["account"], form.cleaned_data["amount"], form.cleaned_data["method"], form.cleaned_data["reference"], form.cleaned_data["notes"]), "Payment posted and expense recorded.")
    messages.error(request, "; ".join(str(error) for errors in form.errors.values() for error in errors))
    return redirect("finance:expense_request_detail", pk=obj.pk)


@login_required
@wpg_permission_required("finance.change_expenserequest", feature_code="FINANCE_EXPENSE_APPROVALS", action="approve")
@require_POST
def expense_request_decide(request, pk, decision):
    obj = get_object_or_404(ExpenseRequest, pk=pk)
    return _run_workflow_action(request, obj, lambda: ExpenseRequestService.return_or_reject(obj, request.user, decision.upper(), request.POST.get("comment")), f"Request {decision.lower()}.")


# =====================================================
# RECEIVABLE LIST
# =====================================================

@login_required
@wpg_permission_required(
    "finance.view_receivable",
    feature_code="FINANCE_RECEIVABLES",
)
def receivable_list(request):
    base_queryset = Receivable.objects.select_related(
        "order", "customer", "counterparty"
    ).order_by("-created_at")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip().lower()

    receivables = base_queryset

    if search:
        receivables = receivables.filter(
            Q(invoice_number__icontains=search)
            | Q(counterparty__name__icontains=search)
            | Q(counterparty__phone__icontains=search)
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

    totals = base_queryset.aggregate(
        total=Sum("total_amount"),
        paid=Sum("amount_paid"),
    )
    total_amount = totals["total"] or 0
    paid_amount = totals["paid"] or 0

    return render(
        request,
        "finance/receivables/receivable_list.html",
        {
            "receivables": receivables,
            "search": search,
            "selected_status": status,
            "status_choices": Receivable.STATUS,
            "total_count": base_queryset.count(),
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "outstanding_amount": total_amount - paid_amount,
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


@login_required
@wpg_permission_required(
    "finance.add_receivable", feature_code="FINANCE_RECEIVABLES", action="add",
)
def receivable_create(request):
    instance = Receivable()
    if request.GET.get("item_group"):
        instance.item_group_id = request.GET["item_group"]
    form = ReceivableForm(request.POST or None, instance=instance, initial={
        "counterparty": request.GET.get("counterparty"),
        "business_unit": request.GET.get("business_unit"),
        "item_group": request.GET.get("item_group"),
    })
    formset = ReceivableLineFormSet(request.POST or None, instance=instance, prefix="lines")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            receivable = ObligationService.create(form=form, formset=formset, kind="receivable")
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, f"Receivable {receivable.invoice_number} created successfully.")
            return redirect("finance:receivable_list")
    return render(request, "finance/receivables/receivable_form.html", {
        "form": form, "formset": formset, "page_title": "Create Receivable",
        "counterparty_create_url": "finance:counterparty_phone_lookup", "obligation_kind": "receivable",
        "group_create_url": "finance:obligation_item_group_create",
        "item_create_url": "finance:obligation_item_type_create",
    })


# =====================================================
# RECEIVABLE DETAIL
# =====================================================

@login_required
@wpg_permission_required(
    "finance.view_receivable",
    feature_code="FINANCE_RECEIVABLES",
)
def receivable_detail(request, pk):
    receivable = get_object_or_404(
        Receivable.objects.select_related(
            "order",
            "customer",
            "counterparty",
        ).prefetch_related(
            "payment_set",
            "lines",
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
@wpg_permission_required(
    "finance.add_payment",
    feature_code="FINANCE_PAYMENTS",
    action="add",
)
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
@wpg_permission_required(
    "finance.view_payable",
    feature_code="FINANCE_PAYABLES",
)
def payable_list(request):
    base_queryset = (
        Payable.objects
        .select_related(
            "supplier",
            "counterparty",
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
            | Q(counterparty__name__icontains=search)
            | Q(counterparty__phone__icontains=search)
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
@wpg_permission_required(
    "finance.add_payable",
    feature_code="FINANCE_PAYABLES",
    action="add",
)
def payable_create(request):
    instance = Payable()
    if request.GET.get("item_group"):
        instance.item_group_id = request.GET["item_group"]
    form = PayableForm(request.POST or None, instance=instance, initial={
        "counterparty": request.GET.get("counterparty"),
        "business_unit": request.GET.get("business_unit"),
        "item_group": request.GET.get("item_group"),
    })
    formset = PayableLineFormSet(request.POST or None, instance=instance, prefix="lines")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            payable = ObligationService.create(form=form, formset=formset, kind="payable")
        except ValidationError as error:
            form.add_error(None, _validation_message(error))
        else:
            messages.success(request, f"Payable {payable.reference} created successfully.")
            return redirect("finance:payable_list")

    return render(
        request,
        "finance/payables/payable_form.html",
        {
            "form": form,
            "formset": formset,
            "page_title": "Create Payable",
            "counterparty_create_url": "finance:counterparty_phone_lookup",
            "obligation_kind": "payable",
            "group_create_url": "finance:obligation_item_group_create",
            "item_create_url": "finance:obligation_item_type_create",
        },
    )


def _catalog_return_url(kind):
    return "finance:payable_create" if kind == "payable" else "finance:receivable_create"


@login_required
@wpg_permission_required("finance.add_payable", feature_code="FINANCE_PAYABLES", action="add")
def obligation_item_group_create(request):
    kind = request.GET.get("next") or request.POST.get("next") or "receivable"
    form = ObligationItemGroupForm(request.POST or None, initial={"business_unit": request.GET.get("business_unit")})
    if request.method == "POST" and form.is_valid():
        group = form.save()
        messages.success(request, f"Item group {group.name} added successfully.")
        return redirect(f"{redirect(_catalog_return_url(kind)).url}?business_unit={group.business_unit}&item_group={group.pk}")
    return render(request, "finance/catalog/item_group_form.html", {"form": form, "kind": kind})


@login_required
@wpg_permission_required("finance.add_payable", feature_code="FINANCE_PAYABLES", action="add")
def obligation_item_type_create(request):
    kind = request.GET.get("next") or request.POST.get("next") or "receivable"
    form = ObligationItemTypeForm(request.POST or None, initial={"item_group": request.GET.get("item_group")})
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"Item {item.name} added successfully.")
        return redirect(f"{redirect(_catalog_return_url(kind)).url}?business_unit={item.item_group.business_unit}&item_group={item.item_group_id}")
    return render(request, "finance/catalog/item_type_form.html", {"form": form, "kind": kind})


@login_required
def obligation_item_groups_json(request):
    groups = ObligationItemGroup.objects.filter(
        is_active=True,
        business_unit=request.GET.get("business_unit", ""),
    ).values("id", "name")
    return JsonResponse({"results": list(groups)})


@login_required
def obligation_item_types_json(request):
    item_group_id = request.GET.get("item_group")
    if not item_group_id:
        return JsonResponse({"results": []})
    items = ObligationItemType.objects.filter(
        is_active=True,
        item_group_id=item_group_id,
    ).values("id", "name", "default_unit")
    return JsonResponse({"results": list(items)})


# =====================================================
# PAYABLE DETAIL
# =====================================================

@login_required
@wpg_permission_required(
    "finance.view_payable",
    feature_code="FINANCE_PAYABLES",
)
def payable_detail(request, pk):
    payable = get_object_or_404(
        Payable.objects.select_related(
            "supplier",
            "counterparty",
        ).prefetch_related(
            "lines",
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
@wpg_permission_required(
    "finance.add_payment",
    feature_code="FINANCE_PAYMENTS",
    action="add",
)
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
@wpg_permission_required(
    "finance.view_payment",
    feature_code="FINANCE_PAYMENTS",
)
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
@wpg_permission_required(
    "finance.view_payroll",
    feature_code="FINANCE_PAYROLL",
)
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
@wpg_permission_required(
    "finance.view_transaction",
    feature_code="FINANCE_REPORTS",
)
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
@wpg_permission_required(
    "finance.view_debtrecord",
    feature_code="FINANCE_DEBTS",
)
def debt_list(request):
    report = DebtReportService.build(request.GET)
    return render(request, "finance/counterparties/debt_list.html", {
        **report, "page_title": "Debt Report", "filters": request.GET,
        "status_choices": Receivable.STATUS, "business_units": DebtRecord.BUSINESS_UNITS,
    })


@login_required
@wpg_permission_required("finance.view_debtrecord", feature_code="FINANCE_DEBTS")
def debt_report_csv(request):
    report = DebtReportService.build(request.GET)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="wpg-debt-report.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Direction", "Reference", "Person / Company", "Phone", "Date", "Due date", "Business unit", "Total RWF", "Paid RWF", "Balance RWF", "Status"])
    for row in report["rows"]:
        writer.writerow([row["direction"], row["reference"], row["party"], row["phone"], row["date"], row["due_date"], row["business_unit"], row["total"], row["paid"], row["balance"], row["status"]])
    writer.writerow([])
    writer.writerow(["Receivable balance", report["receivable_balance"]])
    writer.writerow(["Payable balance", report["payable_balance"]])
    writer.writerow(["Net position", report["net"]])
    return response


@login_required
@wpg_permission_required("finance.view_debtrecord", feature_code="FINANCE_DEBTS")
def debt_report_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    report = DebtReportService.build(request.GET)
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    data = [["Type", "Reference", "Person / Company", "Date", "Due", "Total", "Paid", "Balance", "Status"]]
    for row in report["rows"]:
        data.append([row["direction"], row["reference"], row["party"], str(row["date"]), str(row["due_date"] or "—"), f'{row["total"]:,.0f}', f'{row["paid"]:,.0f}', f'{row["balance"]:,.0f}', row["status"].title()])
    table = Table(data, repeatRows=1, colWidths=[55, 90, 140, 60, 60, 70, 70, 70, 55])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123047")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 7), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")])]))
    story = [Paragraph("WPG Debt Report", styles["Title"]), Paragraph(f'Receivables: RWF {report["receivable_balance"]:,.0f} &nbsp;&nbsp; Payables: RWF {report["payable_balance"]:,.0f} &nbsp;&nbsp; Net: RWF {report["net"]:,.0f}', styles["Normal"]), Spacer(1, 12), table]
    document.build(story)
    response = HttpResponse(stream.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="wpg-debt-report.pdf"'
    return response
