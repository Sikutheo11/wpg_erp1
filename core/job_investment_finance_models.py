from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


ZERO = Decimal("0.00")


class JobFinanceIncomeLink(models.Model):
    job_investment = models.ForeignKey(
        "core.JobInvestment",
        on_delete=models.CASCADE,
        related_name="finance_income_links",
    )
    income_declaration = models.OneToOneField(
        "finance.IncomeDeclaration",
        on_delete=models.PROTECT,
        related_name="job_investment_revenue_link",
    )
    amount_snapshot = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]

    def clean(self):
        declaration = self.income_declaration
        if declaration.status != "FINANCE_CONFIRMED":
            raise ValidationError(
                {"income_declaration": "Only Finance-confirmed income can be linked."}
            )
        if declaration.source_type == "INVESTMENT":
            raise ValidationError(
                {"income_declaration": "Investor capital is funding, not job revenue."}
            )
        if declaration.business_unit != self.job_investment.order.business_unit:
            raise ValidationError(
                {"income_declaration": "Income business unit must match the job order."}
            )

    def save(self, *args, **kwargs):
        self.amount_snapshot = Decimal(str(self.income_declaration.amount))
        self.full_clean()
        return super().save(*args, **kwargs)


class JobFinanceExpenseLink(models.Model):
    ALLOWED_STATUSES = {"PAID", "ACCOUNTABILITY_PENDING", "COMPLETED"}

    job_investment = models.ForeignKey(
        "core.JobInvestment",
        on_delete=models.CASCADE,
        related_name="finance_expense_links",
    )
    expense_request = models.OneToOneField(
        "finance.ExpenseRequest",
        on_delete=models.PROTECT,
        related_name="job_investment_cost_link",
    )
    amount_snapshot = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]

    def clean(self):
        expense = self.expense_request
        if expense.status not in self.ALLOWED_STATUSES:
            raise ValidationError(
                {"expense_request": "Only paid Finance expense requests can be linked."}
            )
        if Decimal(str(expense.amount_paid or 0)) <= 0:
            raise ValidationError(
                {"expense_request": "The Finance expense has no paid amount."}
            )
        if expense.business_unit != self.job_investment.order.business_unit:
            raise ValidationError(
                {"expense_request": "Expense business unit must match the job order."}
            )

    def save(self, *args, **kwargs):
        self.amount_snapshot = Decimal(str(self.expense_request.amount_paid or 0))
        self.full_clean()
        return super().save(*args, **kwargs)
