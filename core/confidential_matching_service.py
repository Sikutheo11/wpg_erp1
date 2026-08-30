from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from core.confidential_capital_models import CapitalProviderMandate, FundingMatch
from core.confidential_funding_offer_models import ContractorFundingOffer


class ConfidentialMatchingService:
    """Score private contractor offers against private provider mandates.

    Identity is deliberately excluded from scoring and from the anonymous
    opportunity snapshot.
    """

    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    WEIGHTS = {
        "capital": Decimal("30.00"),
        "return": Decimal("25.00"),
        "duration": Decimal("20.00"),
        "business_unit": Decimal("10.00"),
        "controlled_account": Decimal("10.00"),
        "security": Decimal("5.00"),
    }

    @classmethod
    def money(cls, value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @classmethod
    def percent(cls, value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @classmethod
    def _binary_score(cls, condition):
        return cls.HUNDRED if condition else cls.ZERO

    @classmethod
    def score(cls, offer, mandate):
        if offer.status not in {"VERIFIED", "MATCHING", "MATCHED"}:
            raise ValidationError("Only a verified contractor offer can be matched.")
        if mandate.status != "ACTIVE":
            raise ValidationError("Only an active capital-provider mandate can be matched.")

        capital_ok = (
            mandate.minimum_capital
            <= offer.capital_required
            <= mandate.maximum_capital
        )
        return_ok = offer.offered_return_percent >= mandate.minimum_return_percent
        duration_ok = offer.expected_duration_days <= mandate.maximum_duration_days

        business_unit = offer.job_investment.order.business_unit
        accepted_units = mandate.preferred_business_units or []
        unit_ok = not accepted_units or business_unit in accepted_units

        controlled_account_ok = (
            not mandate.requires_controlled_project_account
            or offer.controlled_project_account_accepted
        )
        security_ok = not mandate.requires_security or offer.security_available

        raw = {
            "capital": cls._binary_score(capital_ok),
            "return": cls._binary_score(return_ok),
            "duration": cls._binary_score(duration_ok),
            "business_unit": cls._binary_score(unit_ok),
            "controlled_account": cls._binary_score(controlled_account_ok),
            "security": cls._binary_score(security_ok),
        }

        weighted = sum(
            (raw[key] * cls.WEIGHTS[key] / cls.HUNDRED for key in raw),
            cls.ZERO,
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        breakdown = {
            key: {
                "score": str(raw[key]),
                "weight": str(cls.WEIGHTS[key]),
            }
            for key in raw
        }
        return weighted, breakdown

    @classmethod
    def anonymous_snapshot(cls, offer):
        investment = offer.job_investment
        order = investment.order
        return {
            "business_unit": order.business_unit,
            "contract_value": str(cls.money(investment.contract_value)),
            "capital_required": str(cls.money(offer.capital_required)),
            "offered_return_percent": str(cls.percent(offer.offered_return_percent)),
            "agreed_return_amount": str(cls.money(offer.agreed_return_amount)),
            "total_repayment": str(cls.money(offer.total_repayment)),
            "expected_duration_days": offer.expected_duration_days,
            "security_available": offer.security_available,
            "controlled_project_account_accepted": offer.controlled_project_account_accepted,
            "contract_verified": offer.status in {"VERIFIED", "MATCHING", "MATCHED", "FUNDED", "CLOSED"},
        }

    @classmethod
    @transaction.atomic
    def create_or_refresh_match(cls, offer, mandate, *, actor=None):
        score, breakdown = cls.score(offer, mandate)
        match, _ = FundingMatch.objects.get_or_create(
            job_investment=offer.job_investment,
            mandate=mandate,
            defaults={"created_by": actor},
        )
        match.match_score = score
        match.score_breakdown = breakdown
        match.anonymous_opportunity_snapshot = cls.anonymous_snapshot(offer)
        if match.status in {"DECLINED", "EXPIRED"}:
            match.status = "CANDIDATE"
        match.save()

        if offer.status == "VERIFIED":
            offer.status = "MATCHING"
            offer.save(update_fields=["status", "updated_at"])

        return match

    @classmethod
    @transaction.atomic
    def generate_candidates(cls, offer, *, actor=None, minimum_score=Decimal("70.00")):
        candidates = []
        for mandate in CapitalProviderMandate.objects.filter(status="ACTIVE"):
            score, _ = cls.score(offer, mandate)
            if score >= Decimal(str(minimum_score)):
                candidates.append(
                    cls.create_or_refresh_match(offer, mandate, actor=actor)
                )
        return sorted(candidates, key=lambda item: item.match_score, reverse=True)
