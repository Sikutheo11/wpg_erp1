from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from orders.models import Order

from .job_investment_forms import (
    JobActualResultForm,
    JobInvestmentOpenForm,
    JobInvestorAgreementForm,
    JobInvestorContributionForm,
)
from .job_investment_models import JobInvestment, JobInvestorAgreement
from .job_investment_finance_forms import (
    JobFinanceExpenseLinkForm,
    JobFinanceIncomeLinkForm,
)
from .job_investment_finance_service import JobInvestmentFinanceService
from .job_investment_repayment_service import JobInvestorRepaymentService
from .permissions import wpg_permission_required
from .job_investment_service import JobInvestmentService


def _error_text(exc):
    if getattr(exc, "message_dict", None):
        parts = []
        for field, msgs in exc.message_dict.items():
            parts.extend(f"{field}: {msg}" for msg in msgs)
        return "; ".join(parts)
    if getattr(exc, "messages", None):
        return "; ".join(exc.messages)
    return str(exc)


@login_required
@wpg_permission_required("orders.view_order", feature_code="ORDER_LIST")
def job_investment_list(request):
    status_filter = request.GET.get("status", "").strip()
    business_unit_filter = request.GET.get("business_unit", "").strip()

    queryset = (
        JobInvestment.objects.select_related("order", "opened_by")
        .prefetch_related(
            "investor_agreements__investor",
            "investor_agreements__settlement",
            "investor_contributions",
            "finance_income_links",
            "finance_expense_links",
        )
        .order_by("-created_at")
    )

    valid_statuses = {value for value, _label in JobInvestment.STATUSES}
    business_unit_choices = tuple(
        Order._meta.get_field("business_unit").choices or ()
    )
    valid_business_units = {value for value, _label in business_unit_choices}

    if status_filter in valid_statuses:
        queryset = queryset.filter(status=status_filter)
    else:
        status_filter = ""

    if business_unit_filter in valid_business_units:
        queryset = queryset.filter(order__business_unit=business_unit_filter)
    else:
        business_unit_filter = ""

    investments = list(queryset)
    zero = Decimal("0.00")

    summary = {
        "job_count": len(investments),
        "contract_value": sum((item.contract_value for item in investments), zero),
        "estimated_cost": sum((item.estimated_job_cost for item in investments), zero),
        "estimated_profit": sum((item.estimated_profit for item in investments), zero),
        "wpg_capital": sum((item.wpg_capital_committed for item in investments), zero),
        "investor_capital": sum((item.investor_capital_received for item in investments), zero),
        "funding_gap": sum((item.funding_gap for item in investments), zero),
        "actual_revenue": sum((item.actual_revenue_snapshot for item in investments), zero),
        "actual_cost": sum((item.actual_cost_snapshot for item in investments), zero),
        "actual_profit": sum((item.actual_profit_snapshot for item in investments), zero),
    }

    return render(
        request,
        "core/job_investment/list.html",
        {
            "investments": investments,
            "summary": summary,
            "status_choices": JobInvestment.STATUSES,
            "business_unit_choices": business_unit_choices,
            "selected_status": status_filter,
            "selected_business_unit": business_unit_filter,
        },
    )


@login_required
@wpg_permission_required("orders.view_order", feature_code="ORDER_LIST")
def job_investment_eligible_orders(request):
    orders = list(
        Order.objects.filter(business_unit="FURNITURE")
        .exclude(status="CANCELLED")
        .filter(job_investment__isnull=True)
        .select_related("customer_quotation")
        .prefetch_related("furniture_production_plans")
        .order_by("-created_at")
    )

    for order in orders:
        plans = list(order.furniture_production_plans.all())
        usable_plans = [
            plan for plan in plans
            if plan.status in {"CALCULATED", "APPROVED"}
        ]
        order.job_investment_plan_count = len(plans)
        order.job_investment_usable_plan_count = len(usable_plans)
        order.job_investment_estimated_cost = sum(
            (Decimal(str(plan.estimated_total_cost or 0)) for plan in usable_plans),
            Decimal("0.00"),
        )
        order.job_investment_ready = (
            bool(plans)
            and len(usable_plans) == len(plans)
            and order.job_investment_estimated_cost > 0
        )
        order.job_investment_contract_value = (
            order.customer_quotation.total_amount
            if order.customer_quotation_id
            else order.total_amount
        )

    return render(
        request,
        "core/job_investment/eligible_orders.html",
        {"eligible_orders": orders},
    )


@login_required
@wpg_permission_required("orders.view_order", feature_code="ORDER_LIST")
def job_investment_open(request, order_pk):
    order = get_object_or_404(
        Order.objects.select_related("customer_quotation").prefetch_related(
            "furniture_production_plans"
        ),
        pk=order_pk,
    )

    existing = getattr(order, "job_investment", None)
    if existing is not None:
        return redirect("core:job_investment_detail", pk=existing.pk)

    plans = order.furniture_production_plans.all()
    estimated_cost_preview = sum(
        (
            plan.estimated_total_cost
            for plan in plans
            if plan.status in {"CALCULATED", "APPROVED"}
        ),
        0,
    )
    contract_value_preview = (
        order.customer_quotation.total_amount
        if order.customer_quotation_id
        else order.total_amount
    )
    estimated_profit_preview = (
        Decimal(str(contract_value_preview or 0))
        - Decimal(str(estimated_cost_preview or 0))
    )

    form = JobInvestmentOpenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            investment = JobInvestmentService.create_or_refresh_from_order(
                order,
                wpg_capital_committed=form.cleaned_data["wpg_capital_committed"],
                actor=request.user,
            )
            investment.notes = form.cleaned_data["notes"]
            investment.save(update_fields=["notes", "updated_at"])
            messages.success(request, "Job funding record opened successfully.")
            return redirect("core:job_investment_detail", pk=investment.pk)
        except ValidationError as exc:
            messages.error(request, _error_text(exc))

    return render(
        request,
        "core/job_investment/open.html",
        {
            "order": order,
            "form": form,
            "estimated_cost_preview": estimated_cost_preview,
            "contract_value_preview": contract_value_preview,
            "estimated_profit_preview": estimated_profit_preview,
            "plans": plans,
        },
    )


@login_required
@wpg_permission_required("orders.view_order", feature_code="ORDER_LIST")
def job_investment_detail(request, pk):
    investment = get_object_or_404(
        JobInvestment.objects.select_related(
            "order",
            "order__customer_quotation",
            "opened_by",
        ).prefetch_related(
            "investor_agreements__investor",
            "investor_agreements__contributions",
            "investor_contributions__agreement__investor",
            "finance_income_links__income_declaration",
            "finance_expense_links__expense_request",
            "investor_agreements__settlement__finance_debt_record",
        ),
        pk=pk,
    )

    return render(
        request,
        "core/job_investment/detail.html",
        {
            "investment": investment,
            "order": investment.order,
            "agreement_form": JobInvestorAgreementForm(),
            "contribution_form": JobInvestorContributionForm(
                job_investment=investment
            ),
            "actual_result_form": JobActualResultForm(
                initial={
                    "actual_revenue": investment.actual_revenue_snapshot,
                    "actual_cost": investment.actual_cost_snapshot,
                }
            ),
            "finance_income_form": JobFinanceIncomeLinkForm(job_investment=investment),
            "finance_expense_form": JobFinanceExpenseLinkForm(job_investment=investment),
        },
    )


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_refresh(request, pk):
    investment = get_object_or_404(
        JobInvestment.objects.select_related("order"),
        pk=pk,
    )
    try:
        JobInvestmentService.create_or_refresh_from_order(
            investment.order,
            wpg_capital_committed=investment.wpg_capital_committed,
            actor=request.user,
        )
        messages.success(request, "Contract value and estimated job cost refreshed.")
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_update_wpg_capital(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    form = JobInvestmentOpenForm(request.POST)
    if form.is_valid():
        try:
            JobInvestmentService.create_or_refresh_from_order(
                investment.order,
                wpg_capital_committed=form.cleaned_data["wpg_capital_committed"],
                actor=request.user,
            )
            investment.refresh_from_db()
            investment.notes = form.cleaned_data["notes"]
            investment.save(update_fields=["notes", "updated_at"])
            messages.success(request, "WPG committed capital updated.")
        except ValidationError as exc:
            messages.error(request, _error_text(exc))
    else:
        messages.error(request, "Enter a valid WPG capital amount.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_add_agreement(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    form = JobInvestorAgreementForm(request.POST)
    if form.is_valid():
        agreement = form.save(commit=False)
        agreement.job_investment = investment
        agreement.created_by = request.user
        try:
            agreement.save()
            messages.success(request, "Investor agreement added.")
        except ValidationError as exc:
            messages.error(request, _error_text(exc))
    else:
        messages.error(request, "Correct the investor agreement details.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.approve_investor_agreement")
def job_investment_approve_agreement(request, agreement_pk):
    agreement = get_object_or_404(JobInvestorAgreement, pk=agreement_pk)
    if agreement.status != "DRAFT":
        messages.error(request, "Only a draft agreement can be activated.")
    else:
        agreement.status = "ACTIVE"
        agreement.approved_by = request.user
        agreement.approved_at = timezone.now()
        agreement.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        messages.success(request, "Investor agreement activated.")
    return redirect(
        "core:job_investment_detail",
        pk=agreement.job_investment_id,
    )


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_add_contribution(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    form = JobInvestorContributionForm(
        request.POST,
        job_investment=investment,
    )
    if form.is_valid():
        contribution = form.save(commit=False)
        contribution.recorded_by = request.user
        try:
            contribution.save()
            messages.success(request, "Investor contribution recorded.")
        except ValidationError as exc:
            messages.error(request, _error_text(exc))
    else:
        messages.error(request, "Correct the contribution details.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_update_actual_result(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    form = JobActualResultForm(request.POST)
    if form.is_valid():
        investment.actual_revenue_snapshot = form.cleaned_data["actual_revenue"]
        investment.actual_cost_snapshot = form.cleaned_data["actual_cost"]
        investment.save(
            update_fields=[
                "actual_revenue_snapshot",
                "actual_cost_snapshot",
                "updated_at",
            ]
        )
        messages.success(request, "Verified actual result updated.")
    else:
        messages.error(request, "Enter valid revenue and cost values.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.settle_job_investor")
def job_investment_prepare_settlement(request, agreement_pk):
    agreement = get_object_or_404(
        JobInvestorAgreement.objects.select_related("job_investment"),
        pk=agreement_pk,
    )
    try:
        settlement = JobInvestmentService.prepare_investor_settlement(
            agreement
        )
        messages.success(
            request,
            f"Settlement prepared: {settlement.total_due:,.0f} RWF due.",
        )
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect(
        "core:job_investment_detail",
        pk=agreement.job_investment_id,
    )


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_link_income(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    form = JobFinanceIncomeLinkForm(request.POST, job_investment=investment)
    if form.is_valid():
        try:
            JobInvestmentFinanceService.link_income(
                investment, form.cleaned_data["income_declaration"]
            )
            messages.success(request, "Finance-confirmed revenue linked.")
        except ValidationError as exc:
            messages.error(request, _error_text(exc))
    else:
        messages.error(request, "Select an eligible Finance-confirmed revenue record.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_link_expense(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    form = JobFinanceExpenseLinkForm(request.POST, job_investment=investment)
    if form.is_valid():
        try:
            JobInvestmentFinanceService.link_expense(
                investment, form.cleaned_data["expense_request"]
            )
            messages.success(request, "Paid Finance expense linked.")
        except ValidationError as exc:
            messages.error(request, _error_text(exc))
    else:
        messages.error(request, "Select an eligible paid Finance expense.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.manage_job_investment")
def job_investment_sync_finance(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    JobInvestmentFinanceService.sync_actuals(investment)
    messages.success(request, "Actual revenue, cost and profit synced from Finance.")
    return redirect("core:job_investment_detail", pk=pk)


@login_required
@require_POST
@wpg_permission_required("core.settle_job_investor")
def job_investment_post_settlement(request, agreement_pk):
    agreement = get_object_or_404(
        JobInvestorAgreement.objects.select_related("job_investment", "investor"),
        pk=agreement_pk,
    )
    try:
        settlement = JobInvestmentFinanceService.post_settlement_to_finance(
            agreement, actor=request.user
        )
        messages.success(
            request,
            f"Investor settlement posted to Finance as {settlement.finance_debt_record.reference}.",
        )
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect("core:job_investment_detail", pk=agreement.job_investment_id)


@login_required
@require_POST
@wpg_permission_required("core.settle_job_investor")
def job_investment_sync_repayment(request, settlement_pk):
    from .job_investment_models import JobInvestorSettlement

    settlement = get_object_or_404(
        JobInvestorSettlement.objects.select_related("agreement__job_investment"),
        pk=settlement_pk,
    )
    investment_id = settlement.agreement.job_investment_id
    try:
        settlement = JobInvestorRepaymentService.sync_settlement_from_finance(settlement)
        messages.success(
            request,
            f"Repayment synced: {settlement.amount_paid:,.0f} RWF paid; "
            f"{settlement.balance_due:,.0f} RWF balance.",
        )
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    return redirect("core:job_investment_detail", pk=investment_id)


@login_required
@require_POST
@wpg_permission_required("core.settle_job_investor")
def job_investment_sync_all_repayments(request, pk):
    investment = get_object_or_404(JobInvestment, pk=pk)
    synced = JobInvestorRepaymentService.sync_all_for_investment(investment)
    messages.success(request, f"Synced {len(synced)} repayment record(s) from Finance.")
    return redirect("core:job_investment_detail", pk=pk)
