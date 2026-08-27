from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance.models import DebtRecord

from .job_investment_models import JobInvestment, JobInvestorSettlement


class JobInvestorRepaymentService:
    @classmethod
    @transaction.atomic
    def sync_settlement_from_finance(cls, settlement):
        settlement = (
            JobInvestorSettlement.objects
            .select_for_update()
            .select_related(
                "agreement",
                "agreement__job_investment",
            )
            .get(pk=settlement.pk)
        )

        debt = None
        if settlement.finance_debt_record_id:
            debt = (
                DebtRecord.objects
                .select_for_update()
                .get(pk=settlement.finance_debt_record_id)
            )
        if debt is None:
            raise ValidationError(
                "Post the investor settlement to Finance before syncing repayment."
            )

        if debt.direction != DebtRecord.WE_OWE_THEM:
            raise ValidationError(
                "The linked Finance debt must represent money WPG owes the investor."
            )

        paid = Decimal(str(debt.amount_paid or 0))
        total = Decimal(str(settlement.total_due or 0))

        if paid < 0:
            raise ValidationError("Finance paid amount cannot be negative.")
        if paid > total:
            raise ValidationError(
                "Finance paid amount cannot exceed the investor settlement total."
            )

        settlement.amount_paid = paid

        if total > 0 and paid >= total:
            settlement.status = "SETTLED"
            settlement.settled_at = settlement.settled_at or timezone.now()
        elif paid > 0:
            settlement.status = "PARTIAL"
            settlement.settled_at = None
        else:
            settlement.status = "APPROVED"
            settlement.settled_at = None

        settlement.save(
            update_fields=[
                "amount_paid",
                "status",
                "settled_at",
                "updated_at",
            ]
        )

        agreement = settlement.agreement
        agreement.status = (
            "SETTLED"
            if settlement.status == "SETTLED"
            else "SETTLEMENT_DUE"
        )
        agreement.save(update_fields=["status", "updated_at"])

        cls.refresh_investment_status(agreement.job_investment)
        return settlement

    @classmethod
    @transaction.atomic
    def refresh_investment_status(cls, investment):
        investment = (
            JobInvestment.objects
            .select_for_update()
            .get(pk=investment.pk)
        )

        agreements = investment.investor_agreements.exclude(status="CANCELLED")
        if not agreements.exists():
            return investment

        if agreements.exclude(status="SETTLED").exists():
            if investment.status not in {"CANCELLED", "CLOSED"}:
                investment.status = "SETTLEMENT"
                investment.closed_at = None
        else:
            investment.status = "CLOSED"
            investment.closed_at = investment.closed_at or timezone.now()

        investment.save(
            update_fields=[
                "status",
                "closed_at",
                "updated_at",
            ]
        )
        return investment

    @classmethod
    @transaction.atomic
    def sync_all_for_investment(cls, investment):
        settlements = (
            JobInvestorSettlement.objects
            .filter(
                agreement__job_investment=investment,
                finance_debt_record__isnull=False,
            )
            .select_related("finance_debt_record")
        )

        synced = []
        for settlement in settlements:
            synced.append(cls.sync_settlement_from_finance(settlement))

        cls.refresh_investment_status(investment)
        return synced
