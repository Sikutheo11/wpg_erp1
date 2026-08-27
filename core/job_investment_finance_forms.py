from django import forms
from finance.models import ExpenseRequest, IncomeDeclaration


class JobFinanceIncomeLinkForm(forms.Form):
    income_declaration = forms.ModelChoiceField(
        queryset=IncomeDeclaration.objects.none(),
        label="Finance-confirmed job revenue",
    )

    def __init__(self, *args, job_investment=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = IncomeDeclaration.objects.filter(status="FINANCE_CONFIRMED").exclude(
            source_type="INVESTMENT"
        )
        if job_investment is not None:
            qs = qs.filter(
                business_unit=job_investment.order.business_unit,
            ).exclude(job_investment_revenue_link__isnull=False)
        self.fields["income_declaration"].queryset = qs.order_by("-receipt_date", "-pk")
        self.fields["income_declaration"].widget.attrs["class"] = "form-select"


class JobFinanceExpenseLinkForm(forms.Form):
    expense_request = forms.ModelChoiceField(
        queryset=ExpenseRequest.objects.none(),
        label="Paid Finance job expense",
    )

    def __init__(self, *args, job_investment=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = ExpenseRequest.objects.filter(
            status__in=["PAID", "ACCOUNTABILITY_PENDING", "COMPLETED"],
            amount_paid__gt=0,
        )
        if job_investment is not None:
            qs = qs.filter(
                business_unit=job_investment.order.business_unit,
            ).exclude(job_investment_cost_link__isnull=False)
        self.fields["expense_request"].queryset = qs.order_by("-paid_at", "-pk")
        self.fields["expense_request"].widget.attrs["class"] = "form-select"
