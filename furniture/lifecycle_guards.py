from django.core.exceptions import ValidationError

from .lifecycle_evidence import ProductionJobLifecycleEvidence


class ProductionJobTransitionGuard:
    @classmethod
    def assert_can_start_production(cls, job):
        evidence = ProductionJobLifecycleEvidence.build(job)

        if not evidence["order"]["exists"]:
            raise ValidationError(
                "A linked enterprise Order is required before production can start."
            )

        if not evidence["order"]["authorized"]:
            raise ValidationError(
                "The linked Order is not authorized for production."
            )

        if not evidence["plan"]["approved"]:
            raise ValidationError(
                "An approved Production Plan is required before production can start."
            )

        if not evidence["funding"]["ready"]:
            raise ValidationError(evidence["funding"]["message"])

        if not evidence["materials"]["ready"]:
            raise ValidationError(
                "Required materials must be reserved before production can start."
            )

        return evidence

    @classmethod
    def assert_legacy_finished_goods_transition_disabled(cls, job):
        raise ValidationError(
            "Direct QUALITY CHECK → FINISHED GOODS is disabled. "
            "Final quality must be PASSED and APPROVED, then use Release to Inventory."
        )

    @classmethod
    def assert_can_mark_delivered(cls, job):
        evidence = ProductionJobLifecycleEvidence.build(job)

        if job.status != "FINISHED_GOODS":
            raise ValidationError(
                "Only Inventory-released finished goods can be delivered."
            )

        if not evidence["inventory"]["all_output_released"]:
            raise ValidationError(
                "All approved production output must be released to Inventory before delivery."
            )

        if evidence["order"]["exists"] and not evidence["delivery"]["complete"]:
            raise ValidationError(
                "Complete delivery in the Order Engine before marking the Production Job delivered."
            )

        return evidence

    @classmethod
    def assert_can_close(cls, job):
        evidence = ProductionJobLifecycleEvidence.build(job)

        if job.status not in {"DELIVERED", "FINANCE"}:
            raise ValidationError(
                "A Production Job can close only after delivery."
            )

        if evidence["order"]["exists"] and not evidence["delivery"]["complete"]:
            raise ValidationError(
                "Order delivery must be complete before closing the job."
            )

        if evidence["order"]["exists"] and not evidence["finance"]["payment_complete"]:
            raise ValidationError(
                "Customer payment must be reconciled before closing the job."
            )

        investment_status = evidence["finance"]["investment_status"]
        if investment_status and investment_status not in {"CLOSED", "CANCELLED"}:
            raise ValidationError(
                "Close or settle the Job Funding record before closing the Production Job."
            )

        return evidence
