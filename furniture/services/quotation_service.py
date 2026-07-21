from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.approval_service import ApprovalService
from core.event_engine import EventEngine

from furniture.models import (
    Quotation,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
)


class QuotationService:
    """
    Furniture quotation business logic.

    Rules:
    - Quotation.prepared_by and approved_by use Employee.
    - EventEngine actor, AuditLog and notifications use User.
    """

    # =====================================================
    # ACTOR HELPERS
    # =====================================================

    @staticmethod
    def _employee(actor):
        """
        Convert a User or Employee into Employee.
        """

        if actor is None:
            return None

        if hasattr(actor, "employee_code"):
            return actor

        return getattr(
            actor,
            "employee",
            None,
        )

    @staticmethod
    def _user(actor):
        """
        Convert a User or Employee into User.
        """

        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(
            actor,
            "user",
            None,
        )

    @staticmethod
    def _prepared_by_user(quotation):
        """
        Return the User linked to quotation.prepared_by.
        """

        prepared_by = getattr(
            quotation,
            "prepared_by",
            None,
        )

        if prepared_by is None:
            return None

        return getattr(
            prepared_by,
            "user",
            None,
        )

    # =====================================================
    # COST CALCULATION
    # =====================================================

    @staticmethod
    def material_cost(production_job):
        total = Decimal("0.00")

        items = ProductionMaterial.objects.filter(
            production_job=production_job
        )

        for item in items:
            total += (
                item.total_cost
                or Decimal("0.00")
            )

        return total

    @staticmethod
    def labour_cost(production_job):
        total = Decimal("0.00")

        items = ProductionLabour.objects.filter(
            production_job=production_job
        )

        for item in items:
            total += (
                item.total_cost
                or Decimal("0.00")
            )

        return total

    @staticmethod
    def machine_cost(production_job):
        total = Decimal("0.00")

        items = ProductionMachine.objects.filter(
            production_job=production_job
        )

        for item in items:
            total += (
                item.total_cost
                or Decimal("0.00")
            )

        return total

    @classmethod
    def calculate_costs(cls, production_job):
        if production_job is None:
            raise ValidationError(
                "Production job is required."
            )

        return {
            "material_cost": cls.material_cost(
                production_job
            ),
            "labour_cost": cls.labour_cost(
                production_job
            ),
            "machine_cost": cls.machine_cost(
                production_job
            ),
        }

    # =====================================================
    # PREPARE QUOTATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def prepare_quotation(
        cls,
        production_job,
        prepared_by=None,
        transport_cost=Decimal("0.00"),
        other_cost=Decimal("0.00"),
        profit=Decimal("0.00"),
    ):
        if production_job is None:
            raise ValidationError(
                "Production job is required."
            )

        employee = cls._employee(
            prepared_by
        )

        transport_cost = Decimal(
            str(transport_cost or 0)
        )

        other_cost = Decimal(
            str(other_cost or 0)
        )

        profit = Decimal(
            str(profit or 0)
        )

        if transport_cost < 0:
            raise ValidationError(
                "Transport cost cannot be negative."
            )

        if other_cost < 0:
            raise ValidationError(
                "Other cost cannot be negative."
            )

        costs = cls.calculate_costs(
            production_job
        )

        quotation, created = (
            Quotation.objects.get_or_create(
                production_job=production_job,
                defaults={
                    "prepared_by": employee,
                },
            )
        )

        if employee is not None:
            quotation.prepared_by = employee

        quotation.material_cost = (
            costs["material_cost"]
        )

        quotation.labour_cost = (
            costs["labour_cost"]
        )

        quotation.machine_cost = (
            costs["machine_cost"]
        )

        quotation.transport_cost = (
            transport_cost
        )

        quotation.other_cost = (
            other_cost
        )

        quotation.profit = profit

        quotation.selling_price = (
            quotation.material_cost
            + quotation.labour_cost
            + quotation.machine_cost
            + quotation.transport_cost
            + quotation.other_cost
            + quotation.profit
        )

        quotation.status = "DRAFT"

        quotation.save()

        return quotation

    # =====================================================
    # SUBMIT QUOTATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def submit(
        cls,
        quotation,
        actor=None,
    ):
        if quotation.status not in {
            "DRAFT",
            "REJECTED",
        }:
            raise ValidationError(
                (
                    "Only draft or rejected quotations "
                    "can be submitted."
                )
            )

        user = cls._user(actor)

        quotation.status = "SUBMITTED"

        quotation.save(
            update_fields=[
                "status",
            ]
        )

        production_job = (
            quotation.production_job
        )

        if production_job:
            production_job.status = "QUOTATION"

            production_job.save(
                update_fields=[
                    "status",
                ]
            )

        EventEngine.dispatch(
            event_code=(
                "FURNITURE_QUOTATION_SUBMITTED"
            ),
            actor=user,
            obj=quotation,
            title="Quotation Submitted",
            message=(
                f"Quotation #{quotation.pk} "
                "was submitted for approval."
            ),
            level="INFO",
            metadata={
                "quotation_id": quotation.pk,
                "production_job_id": (
                    quotation.production_job_id
                ),
            },
            notify_groups=[
                "Furniture Manager",
                "CEO",
            ],
            notify_owner=True,
        )

        return quotation

    # =====================================================
    # REQUEST APPROVAL
    # =====================================================

    @classmethod
    def request_approval(
        cls,
        quotation,
        requested_by=None,
        reason="Quotation approval request",
    ):
        if quotation.status != "SUBMITTED":
            raise ValidationError(
                (
                    "Only submitted quotations can "
                    "be sent for approval."
                )
            )

        if not quotation.production_job:
            raise ValidationError(
                "Quotation has no production job."
            )

        user = cls._user(
            requested_by
        )

        return ApprovalService.request_approval(
            obj=quotation.production_job,
            workflow_code=(
                "FURNITURE_PRODUCTION"
            ),
            to_step="APPROVED",
            requested_by=user,
            reason=reason,
        )

    # =====================================================
    # APPROVE QUOTATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def approve(
        cls,
        quotation,
        approved_by=None,
        note="Quotation approved",
    ):
        if quotation.status != "SUBMITTED":
            raise ValidationError(
                (
                    "Only submitted quotations "
                    "can be approved."
                )
            )

        employee = cls._employee(
            approved_by
        )

        user = cls._user(
            approved_by
        )

        if employee is None:
            raise ValidationError(
                (
                    "The approving user is not linked "
                    "to an employee record."
                )
            )

        quotation.status = "APPROVED"
        quotation.approved_by = employee

        quotation.save(
            update_fields=[
                "status",
                "approved_by",
            ]
        )

        production_job = (
            quotation.production_job
        )

        if production_job:
            production_job.status = "APPROVED"

            production_job.save(
                update_fields=[
                    "status",
                ]
            )

        prepared_by_user = (
            cls._prepared_by_user(
                quotation
            )
        )

        notify_users = []

        if prepared_by_user is not None:
            notify_users.append(
                prepared_by_user
            )

        EventEngine.dispatch(
            event_code=(
                "FURNITURE_QUOTATION_APPROVED"
            ),
            actor=user,
            obj=quotation,
            title="Quotation Approved",
            message=(
                f"Quotation #{quotation.pk} "
                "has been approved."
            ),
            level="SUCCESS",
            metadata={
                "quotation_id": quotation.pk,
                "production_job_id": (
                    quotation.production_job_id
                ),
                "note": note,
                "approved_at": (
                    timezone.now().isoformat()
                ),
            },
            notify_users=notify_users,
            notify_groups=[
                "Furniture Manager",
            ],
            notify_owner=True,
        )

        return quotation

    # =====================================================
    # REJECT QUOTATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def reject(
        cls,
        quotation,
        rejected_by=None,
        reason="",
    ):
        if quotation.status != "SUBMITTED":
            raise ValidationError(
                (
                    "Only submitted quotations "
                    "can be rejected."
                )
            )

        user = cls._user(
            rejected_by
        )

        quotation.status = "REJECTED"

        quotation.save(
            update_fields=[
                "status",
            ]
        )

        production_job = (
            quotation.production_job
        )

        if (
            production_job
            and production_job.status
            == "APPROVED"
        ):
            production_job.status = "QUOTATION"

            production_job.save(
                update_fields=[
                    "status",
                ]
            )

        prepared_by_user = (
            cls._prepared_by_user(
                quotation
            )
        )

        notify_users = []

        if prepared_by_user is not None:
            notify_users.append(
                prepared_by_user
            )

        EventEngine.dispatch(
            event_code=(
                "FURNITURE_QUOTATION_REJECTED"
            ),
            actor=user,
            obj=quotation,
            title="Quotation Rejected",
            message=(
                f"Quotation #{quotation.pk} "
                "has been rejected."
            ),
            level="WARNING",
            metadata={
                "quotation_id": quotation.pk,
                "production_job_id": (
                    quotation.production_job_id
                ),
                "reason": reason or "",
                "rejected_at": (
                    timezone.now().isoformat()
                ),
            },
            notify_users=notify_users,
            notify_groups=[
                "Furniture Manager",
            ],
            notify_owner=True,
        )

        return quotation