from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from core.event_engine import EventEngine

from furniture.models import (
    ProductionJob,
    QualityInspection,
    ProductionDefect,
    ReworkOrder,
    ProductionTimeline,
)


class QualityService:
    """
    Furniture Quality Inspection Engine.

    Handles:
    - creating inspections
    - recording inspection results
    - creating defects
    - assigning rework
    - starting and completing rework
    - re-inspection
    - final quality approval
    """

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _actor(employee_or_user):
        if employee_or_user is None:
            return None

        if hasattr(employee_or_user, "is_authenticated"):
            return employee_or_user

        return getattr(employee_or_user, "user", None)

    @staticmethod
    def _employee(employee_or_user):
        if employee_or_user is None:
            return None

        if hasattr(employee_or_user, "employee_code"):
            return employee_or_user

        return getattr(employee_or_user, "employee", None)

    @classmethod
    def _timeline(
        cls,
        production_job,
        action,
        performed_by=None,
        note="",
        from_status="",
        to_status="",
    ):
        return ProductionTimeline.objects.create(
            production_job=production_job,
            action=action,
            from_status=from_status or production_job.status,
            to_status=to_status or production_job.status,
            performed_by=cls._employee(performed_by),
            note=note or "",
        )

    @staticmethod
    def _validate_quantities(
        quantity_inspected,
        quantity_passed,
        quantity_failed,
    ):
        if quantity_inspected < 0:
            raise ValidationError(
                "Quantity inspected cannot be negative."
            )

        if quantity_passed < 0 or quantity_failed < 0:
            raise ValidationError(
                "Passed and failed quantities cannot be negative."
            )

        if quantity_passed + quantity_failed > quantity_inspected:
            raise ValidationError(
                "Passed and failed quantities cannot exceed inspected quantity."
            )

    # =====================================================
    # CREATE INSPECTION
    # =====================================================
    @classmethod
    @transaction.atomic
    def create_inspection(
        cls,
        production_job,
        inspector=None,
        inspection_type="FINAL",
        quantity_inspected=0,
        remarks="",
        evidence_image=None,
    ):
        """
        Create a quality inspection according to the production workflow.

        Rules:
        - IN_PROCESS inspection:
            allowed during IN_PRODUCTION or QUALITY_CHECK.
            Does not automatically change the production-job status.

        - FINAL inspection:
            allowed only during QUALITY_CHECK.

        - RE_INSPECTION:
            allowed only during QUALITY_CHECK and should normally follow
            a failed inspection or completed rework.
        """

        inspection_type = str(inspection_type).upper()

        allowed_types = {
            "IN_PROCESS",
            "FINAL",
            "RE_INSPECTION",
        }

        if inspection_type not in allowed_types:
            raise ValidationError(
                {
                    "inspection_type": (
                        "Inspection type must be IN_PROCESS, "
                        "FINAL or RE_INSPECTION."
                    )
                }
            )

        if quantity_inspected is None:
            quantity_inspected = 0

        if quantity_inspected <= 0:
            raise ValidationError(
                {
                    "quantity_inspected": (
                        "Quantity inspected must be greater than zero."
                    )
                }
            )

        if quantity_inspected > production_job.quantity_to_produce:
            raise ValidationError(
                "Quantity inspected cannot exceed the production job quantity."
            )

        # =====================================================
        # VALIDATE JOB STATUS BY INSPECTION TYPE
        # =====================================================

        if inspection_type == "IN_PROCESS":
            allowed_statuses = {
                "IN_PRODUCTION",
                "QUALITY_CHECK",
            }

        elif inspection_type == "FINAL":
            allowed_statuses = {
                "QUALITY_CHECK",
            }

        else:  # RE_INSPECTION
            allowed_statuses = {
                "QUALITY_CHECK",
            }

        if production_job.status not in allowed_statuses:
            raise ValidationError(
                (
                    f"{inspection_type} inspection is not allowed "
                    f"when production job status is "
                    f"{production_job.status}."
                )
            )

        # =====================================================
        # RE-INSPECTION BUSINESS RULE
        # =====================================================

        if inspection_type == "RE_INSPECTION":
            previous_failed_inspection_exists = (
                production_job.quality_inspections.filter(
                    result__in=[
                        "FAILED",
                        "CONDITIONAL",
                    ]
                ).exists()
            )

            completed_rework_exists = (
                production_job.rework_orders.filter(
                    status__in=[
                        "COMPLETED",
                        "VERIFIED",
                    ]
                ).exists()
            )

            if not (
                previous_failed_inspection_exists
                or completed_rework_exists
            ):
                raise ValidationError(
                    (
                        "Re-inspection requires either a previous "
                        "failed/conditional inspection or completed rework."
                    )
                )

        # =====================================================
        # PREVENT DUPLICATE PENDING INSPECTIONS
        # =====================================================

        pending_inspection_exists = (
            QualityInspection.objects.filter(
                production_job=production_job,
                inspection_type=inspection_type,
                result="PENDING",
            ).exists()
        )

        if pending_inspection_exists:
            raise ValidationError(
                (
                    f"A pending {inspection_type.lower()} inspection "
                    "already exists for this production job."
                )
            )

        inspection = QualityInspection.objects.create(
            production_job=production_job,
            inspection_type=inspection_type,
            inspector=cls._employee(inspector),
            result="PENDING",
            passed=False,
            score=0,
            quantity_inspected=quantity_inspected,
            quantity_passed=0,
            quantity_failed=0,
            remarks=remarks or "",
            evidence_image=evidence_image,
        )

        # =====================================================
        # STATUS HANDLING
        # =====================================================

        old_status = production_job.status

        # An in-process inspection should not interrupt production.
        # FINAL and RE_INSPECTION already require QUALITY_CHECK.
        new_status = production_job.status

        if (
            inspection_type in {
                "FINAL",
                "RE_INSPECTION",
            }
            and production_job.status != "QUALITY_CHECK"
        ):
            new_status = "QUALITY_CHECK"
            production_job.status = new_status
            production_job.save(
                update_fields=[
                    "status",
                ]
            )

        cls._timeline(
            production_job=production_job,
            action=(
                f"{inspection.get_inspection_type_display()} created"
            ),
            performed_by=inspector,
            note=(
                remarks
                or f"Inspection #{inspection.pk} created."
            ),
            from_status=old_status,
            to_status=new_status,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_QUALITY_INSPECTION_CREATED",
            actor=cls._actor(inspector),
            obj=inspection,
            title="Quality Inspection Created",
            message=(
                f"{inspection.get_inspection_type_display()} "
                f"#{inspection.pk} was created for "
                f"production job #{production_job.pk}."
            ),
            level="INFO",
            metadata={
                "inspection_id": inspection.pk,
                "production_job_id": production_job.pk,
                "inspection_type": inspection_type,
                "quantity_inspected": quantity_inspected,
                "job_status": production_job.status,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )

        return inspection

    # =====================================================
    # RECORD RESULT
    # =====================================================

    @classmethod
    @transaction.atomic
    def record_result(
        cls,
        inspection,
        result,
        score,
        quantity_inspected,
        quantity_passed,
        quantity_failed,
        inspector=None,
        remarks="",
        evidence_image=None,
    ):
        result = str(result).upper()

        allowed_results = {
            "PASSED",
            "FAILED",
            "CONDITIONAL",
        }

        if inspection.result != "PENDING":
            raise ValidationError(
                "A recorded inspection result cannot be changed. Create a re-inspection instead."
            )

        if result not in allowed_results:
            raise ValidationError(
                "Inspection result must be PASSED, FAILED or CONDITIONAL."
            )

        if score < 0 or score > 100:
            raise ValidationError(
                "Quality score must be between 0 and 100."
            )

        cls._validate_quantities(
            quantity_inspected,
            quantity_passed,
            quantity_failed,
        )

        if quantity_passed + quantity_failed != quantity_inspected:
            raise ValidationError(
                "Passed and failed quantities must equal inspected quantity."
            )

        if result == "PASSED" and quantity_failed > 0:
            raise ValidationError(
                "A passed inspection cannot contain failed units."
            )

        inspection.result = result
        inspection.passed = result == "PASSED"
        inspection.score = score
        inspection.quantity_inspected = quantity_inspected
        inspection.quantity_passed = quantity_passed
        inspection.quantity_failed = quantity_failed
        inspection.inspector = (
            cls._employee(inspector)
            or inspection.inspector
        )
        inspection.remarks = remarks or inspection.remarks

        if evidence_image is not None:
            inspection.evidence_image = evidence_image

        inspection.inspected_at = timezone.now()

        inspection.save(
            update_fields=[
                "result",
                "passed",
                "score",
                "quantity_inspected",
                "quantity_passed",
                "quantity_failed",
                "inspector",
                "remarks",
                "evidence_image",
                "inspected_at",
                "updated_at",
            ]
        )

        cls._timeline(
            production_job=inspection.production_job,
            action=f"Quality inspection {result.lower()}",
            performed_by=inspector,
            note=remarks,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_QUALITY_RESULT_RECORDED",
            actor=cls._actor(inspector),
            obj=inspection,
            title="Quality Result Recorded",
            message=(
                f"Inspection #{inspection.pk} result: {result}."
            ),
            level="SUCCESS" if result == "PASSED" else "WARNING",
            metadata={
                "inspection_id": inspection.pk,
                "production_job_id": inspection.production_job_id,
                "result": result,
                "score": score,
                "quantity_failed": quantity_failed,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )

        return inspection

    # =====================================================
    # CREATE DEFECT
    # =====================================================

    @classmethod
    @transaction.atomic
    def create_defect(
        cls,
        inspection,
        defect_type,
        severity,
        description,
        affected_quantity=1,
        root_cause="",
        corrective_action="",
        evidence_image=None,
        reported_by=None,
        rework_required=True,
    ):
        if affected_quantity <= 0:
            raise ValidationError(
                "Affected quantity must be greater than zero."
            )

        if inspection.result not in {"FAILED", "CONDITIONAL"}:
            raise ValidationError(
                "Defects can only be recorded for a failed or conditional inspection."
            )

        if affected_quantity > inspection.quantity_failed:
            raise ValidationError(
                "Affected quantity cannot exceed the inspection failed quantity."
            )

        status = (
            "REWORK_REQUIRED"
            if rework_required
            else "OPEN"
        )

        defect = ProductionDefect.objects.create(
            inspection=inspection,
            production_job=inspection.production_job,
            defect_type=defect_type,
            severity=severity,
            description=description,
            affected_quantity=affected_quantity,
            root_cause=root_cause or "",
            corrective_action=corrective_action or "",
            status=status,
            evidence_image=evidence_image,
            reported_by=cls._employee(reported_by),
        )

        if inspection.result == "PASSED":
            inspection.result = "FAILED"
            inspection.passed = False
            inspection.save(
                update_fields=[
                    "result",
                    "passed",
                    "updated_at",
                ]
            )

        cls._timeline(
            production_job=inspection.production_job,
            action="Quality defect recorded",
            performed_by=reported_by,
            note=(
                f"{defect.get_defect_type_display()} "
                f"({defect.get_severity_display()})"
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_QUALITY_DEFECT_RECORDED",
            actor=cls._actor(reported_by),
            obj=defect,
            title="Quality Defect Recorded",
            message=(
                f"A {severity.lower()} defect was recorded "
                f"for production job #{inspection.production_job_id}."
            ),
            level="ERROR" if severity == "CRITICAL" else "WARNING",
            metadata={
                "defect_id": defect.pk,
                "inspection_id": inspection.pk,
                "production_job_id": inspection.production_job_id,
                "severity": severity,
                "affected_quantity": affected_quantity,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )

        return defect

    # =====================================================
    # ASSIGN REWORK
    # =====================================================

    @classmethod
    @transaction.atomic
    def assign_rework(
        cls,
        defect,
        assigned_to,
        instructions,
        estimated_hours=Decimal("0.00"),
        created_by=None,
    ):
        if defect.status in {
            "RESOLVED",
            "SCRAPPED",
            "ACCEPTED",
        }:
            raise ValidationError(
                "A closed defect cannot be assigned for rework."
            )

        if estimated_hours < 0:
            raise ValidationError(
                "Estimated hours cannot be negative."
            )

        if defect.rework_orders.exclude(
            status__in={"VERIFIED", "CANCELLED"},
        ).exists():
            raise ValidationError(
                "This defect already has an active rework order."
            )

        rework = ReworkOrder.objects.create(
            production_job=defect.production_job,
            defect=defect,
            assigned_to=cls._employee(assigned_to),
            status="ASSIGNED",
            instructions=instructions,
            estimated_hours=estimated_hours,
            created_by=cls._employee(created_by),
        )

        defect.status = "REWORK_REQUIRED"
        defect.save(update_fields=["status", "updated_at"])

        cls._timeline(
            production_job=defect.production_job,
            action="Rework assigned",
            performed_by=created_by,
            note=(
                f"{rework.rework_code} assigned to "
                f"{rework.assigned_to or 'Unassigned'}."
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_REWORK_ASSIGNED",
            actor=cls._actor(created_by),
            obj=rework,
            title="Rework Assigned",
            message=(
                f"Rework {rework.rework_code} was assigned."
            ),
            level="INFO",
            metadata={
                "rework_id": rework.pk,
                "defect_id": defect.pk,
                "production_job_id": defect.production_job_id,
            },
            notify_users=[
                cls._actor(assigned_to),
            ],
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
        )

        return rework

    # =====================================================
    # START REWORK
    # =====================================================

    @classmethod
    @transaction.atomic
    def start_rework(
        cls,
        rework,
        performed_by=None,
        note="",
    ):
        if rework.status not in {
            "PENDING",
            "ASSIGNED",
        }:
            raise ValidationError(
                "Only pending or assigned rework can be started."
            )

        rework.status = "IN_PROGRESS"
        rework.started_at = timezone.now()
        rework.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )

        rework.defect.status = "UNDER_REWORK"
        rework.defect.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._timeline(
            production_job=rework.production_job,
            action="Rework started",
            performed_by=performed_by,
            note=note or rework.rework_code,
        )

        return rework

    # =====================================================
    # COMPLETE REWORK
    # =====================================================

    @classmethod
    @transaction.atomic
    def complete_rework(
        cls,
        rework,
        completed_by=None,
        actual_hours=Decimal("0.00"),
        rework_cost=Decimal("0.00"),
        completion_note="",
        completion_image=None,
    ):
        if rework.status != "IN_PROGRESS":
            raise ValidationError(
                "Only rework in progress can be completed."
            )

        if actual_hours < 0:
            raise ValidationError(
                "Actual hours cannot be negative."
            )

        if rework_cost < 0:
            raise ValidationError(
                "Rework cost cannot be negative."
            )

        rework.status = "COMPLETED"
        rework.actual_hours = actual_hours
        rework.rework_cost = rework_cost
        rework.completion_note = completion_note or ""
        rework.completion_image = completion_image
        rework.completed_by = cls._employee(completed_by)
        rework.completed_at = timezone.now()

        rework.save(
            update_fields=[
                "status",
                "actual_hours",
                "rework_cost",
                "completion_note",
                "completion_image",
                "completed_by",
                "completed_at",
                "updated_at",
            ]
        )

        cls._timeline(
            production_job=rework.production_job,
            action="Rework completed",
            performed_by=completed_by,
            note=completion_note or rework.rework_code,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_REWORK_COMPLETED",
            actor=cls._actor(completed_by),
            obj=rework,
            title="Rework Completed",
            message=(
                f"Rework {rework.rework_code} was completed "
                "and is waiting for verification."
            ),
            level="SUCCESS",
            metadata={
                "rework_id": rework.pk,
                "production_job_id": rework.production_job_id,
                "actual_hours": str(actual_hours),
                "rework_cost": str(rework_cost),
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )

        return rework

    # =====================================================
    # VERIFY REWORK
    # =====================================================

    @classmethod
    @transaction.atomic
    def verify_rework(
        cls,
        rework,
        verified_by=None,
        passed=True,
        note="",
    ):
        if rework.status != "COMPLETED":
            raise ValidationError(
                "Only completed rework can be verified."
            )

        if not passed:
            rework.status = "ASSIGNED"
            rework.completed_at = None
            rework.verified_at = None
            rework.completed_by = None
            rework.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "verified_at",
                    "completed_by",
                    "updated_at",
                ]
            )

            rework.defect.status = "REWORK_REQUIRED"
            rework.defect.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            cls._timeline(
                production_job=rework.production_job,
                action="Rework verification failed",
                performed_by=verified_by,
                note=note,
            )

            return rework

        rework.status = "VERIFIED"
        rework.verified_at = timezone.now()
        rework.save(
            update_fields=[
                "status",
                "verified_at",
                "updated_at",
            ]
        )

        rework.defect.resolve(
            employee=cls._employee(verified_by),
            corrective_action=(
                rework.completion_note
                or note
            ),
        )

        cls._timeline(
            production_job=rework.production_job,
            action="Rework verified",
            performed_by=verified_by,
            note=note or rework.rework_code,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_REWORK_VERIFIED",
            actor=cls._actor(verified_by),
            obj=rework,
            title="Rework Verified",
            message=(
                f"Rework {rework.rework_code} passed verification."
            ),
            level="SUCCESS",
            metadata={
                "rework_id": rework.pk,
                "defect_id": rework.defect_id,
                "production_job_id": rework.production_job_id,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
        )

        return rework

    # =====================================================
    # FINAL QUALITY APPROVAL
    # =====================================================

    @classmethod
    @transaction.atomic
    def approve_finished_goods(
        cls,
        inspection,
        approved_by,
        note="",
    ):
        if inspection.result != "PASSED":
            raise ValidationError(
                "Only passed inspections can receive final approval."
            )

        if inspection.inspection_type not in {"FINAL", "RE_INSPECTION"}:
            raise ValidationError(
                "Only a final inspection or re-inspection can approve finished goods."
            )

        if inspection.approved_at is not None:
            raise ValidationError("This inspection is already approved.")

        if inspection.production_job.status != "QUALITY_CHECK":
            raise ValidationError(
                "The production job must be in quality check before final approval."
            )

        unresolved_defects = inspection.production_job.quality_defects.exclude(
            status__in=[
                "RESOLVED",
                "ACCEPTED",
                "SCRAPPED",
            ]
        )

        if unresolved_defects.exists():
            raise ValidationError(
                "All quality defects must be resolved before approval."
            )

        inspection.approved_by = cls._employee(approved_by)
        inspection.approved_at = timezone.now()
        inspection.save(
            update_fields=[
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        job = inspection.production_job
        old_status = job.status
        job.status = "FINISHED_GOODS"
        job.save(update_fields=["status"])

        cls._timeline(
            production_job=job,
            action="Finished goods quality approved",
            performed_by=approved_by,
            note=note,
            from_status=old_status,
            to_status="FINISHED_GOODS",
        )

        EventEngine.dispatch(
            event_code="FURNITURE_QUALITY_APPROVED",
            actor=cls._actor(approved_by),
            obj=inspection,
            title="Finished Goods Approved",
            message=(
                f"Production job #{job.pk} passed final quality approval."
            ),
            level="SUCCESS",
            metadata={
                "inspection_id": inspection.pk,
                "production_job_id": job.pk,
                "from_status": old_status,
                "to_status": "FINISHED_GOODS",
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
                "Store Keeper",
            ],
            notify_owner=True,
        )

        return inspection

    # =====================================================
    # QUALITY SUMMARY
    # =====================================================

    @classmethod
    def job_quality_summary(cls, production_job):
        inspections = production_job.quality_inspections.all()
        defects = production_job.quality_defects.all()
        reworks = production_job.rework_orders.all()

        total_inspections = inspections.count()
        passed_inspections = inspections.filter(
            result="PASSED"
        ).count()
        failed_inspections = inspections.filter(
            result="FAILED"
        ).count()

        pass_rate = Decimal("0.00")

        if total_inspections:
            pass_rate = (
                Decimal(passed_inspections)
                / Decimal(total_inspections)
                * Decimal("100.00")
            ).quantize(Decimal("0.01"))

        return {
            "total_inspections": total_inspections,
            "passed_inspections": passed_inspections,
            "failed_inspections": failed_inspections,
            "pending_inspections": inspections.filter(
                result="PENDING"
            ).count(),
            "conditional_inspections": inspections.filter(
                result="CONDITIONAL"
            ).count(),
            "pass_rate": pass_rate,
            "open_defects": defects.exclude(
                status__in=[
                    "RESOLVED",
                    "ACCEPTED",
                    "SCRAPPED",
                ]
            ).count(),
            "critical_defects": defects.filter(
                severity="CRITICAL"
            ).exclude(
                status__in=[
                    "RESOLVED",
                    "ACCEPTED",
                    "SCRAPPED",
                ]
            ).count(),
            "pending_reworks": reworks.filter(
                status__in=[
                    "PENDING",
                    "ASSIGNED",
                    "IN_PROGRESS",
                    "COMPLETED",
                ]
            ).count(),
            "verified_reworks": reworks.filter(
                status="VERIFIED"
            ).count(),
            "quality_approved": inspections.filter(
                result="PASSED",
                approved_at__isnull=False,
            ).exists(),
        }
