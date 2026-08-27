from django import forms

from .job_investment_models import JobInvestorAgreement, JobInvestorContribution


class BootstrapFormMixin:
    def _bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs.setdefault("class", css)


class JobInvestmentOpenForm(BootstrapFormMixin, forms.Form):
    wpg_capital_committed = forms.DecimalField(
        label="WPG capital committed",
        min_value=0,
        max_digits=18,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"step": "0.01"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


class JobInvestorAgreementForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = JobInvestorAgreement
        fields = [
            "investor",
            "committed_capital",
            "return_model",
            "fixed_profit_amount",
            "profit_share_percent",
            "agreement_date",
            "repayment_due_date",
            "terms",
        ]
        widgets = {
            "agreement_date": forms.DateInput(attrs={"type": "date"}),
            "repayment_due_date": forms.DateInput(attrs={"type": "date"}),
            "terms": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


class JobInvestorContributionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = JobInvestorContribution
        fields = [
            "agreement",
            "amount",
            "status",
            "received_date",
            "payment_reference",
            "finance_income_declaration",
        ]
        widgets = {
            "received_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, job_investment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if job_investment is not None:
            self.fields["agreement"].queryset = (
                job_investment.investor_agreements
                .filter(status__in=["APPROVED", "ACTIVE"])
                .select_related("investor")
            )
        self._bootstrap()


class JobActualResultForm(BootstrapFormMixin, forms.Form):
    actual_revenue = forms.DecimalField(
        label="Verified actual job revenue",
        min_value=0,
        max_digits=18,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01"}),
    )
    actual_cost = forms.DecimalField(
        label="Verified actual job cost",
        min_value=0,
        max_digits=18,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()
