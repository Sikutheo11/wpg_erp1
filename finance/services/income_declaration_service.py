from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import Account, IncomeDeclaration
from .income_service import IncomeService


class IncomeDeclarationService:
    @staticmethod
    def _lock(declaration):
        return IncomeDeclaration.objects.select_for_update().get(pk=declaration.pk)

    @staticmethod
    def _prevent_self_approval(declaration, actor):
        if declaration.recorded_by_id == actor.pk:
            raise PermissionDenied("You cannot approve or confirm income that you recorded.")

    @staticmethod
    def _require_group(actor, *names):
        if not actor.is_superuser and not actor.groups.filter(name__in=names).exists():
            raise PermissionDenied(f"This action requires one of these roles: {', '.join(names)}.")

    @classmethod
    @transaction.atomic
    def submit(cls, declaration, actor):
        obj = cls._lock(declaration)
        if obj.recorded_by_id != actor.pk:
            raise PermissionDenied("Only the recorder can submit this declaration.")
        if obj.status not in {"DRAFT", "RETURNED"}:
            raise ValidationError("Only a draft or returned declaration can be submitted.")
        if not obj.department_id:
            raise ValidationError("Your employee profile must belong to a department before submission.")
        if not obj.department.manager_id:
            raise ValidationError("The department must have an assigned manager before submission.")
        if obj.business_unit != obj.department.business_unit:
            raise ValidationError("The declaration business unit must match the recorder's department.")
        obj.full_clean()
        obj.status = "SUBMITTED"
        obj.save(update_fields=["status", "updated_at"])
        return obj

    @classmethod
    @transaction.atomic
    def unit_approve(cls, declaration, actor, comment=""):
        obj = cls._lock(declaration)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "Manager", "Construction Manager", "Furniture Manager", "Marketplace Manager", "Finance Manager")
        if obj.status != "SUBMITTED":
            raise ValidationError("This declaration is not awaiting unit-manager approval.")
        if obj.department_id and obj.department.manager_id and obj.department.manager_id != actor.pk and not actor.is_superuser:
            raise PermissionDenied("Only the recorder's line manager can approve this declaration.")
        obj.status = "UNIT_APPROVED"
        obj.unit_approved_by = actor
        obj.unit_approved_at = timezone.now()
        obj.unit_comment = (comment or "").strip()
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def finance_confirm(cls, declaration, actor, account, comment=""):
        obj = cls._lock(declaration)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "Accountant", "Finance Manager")
        if obj.status != "UNIT_APPROVED":
            raise ValidationError("This declaration is not awaiting Finance confirmation.")
        if obj.posted_income_id:
            raise ValidationError("This declaration has already been posted.")
        account = Account.objects.select_for_update().get(pk=account.pk)
        type_map = {
            "SALE": "sales", "SERVICE": "service",
            "RENT": "other", "INTEREST": "other", "INVESTMENT": "other",
            "LOAN": "other", "GRANT": "other", "OTHER": "other",
        }
        result = IncomeService.create_income(
            account=account,
            business_unit=obj.business_unit,
            title=obj.title,
            income_type=type_map[obj.source_type],
            amount=obj.amount,
            sale=obj.related_sale,
            received_from=obj.received_from,
            reference=obj.reference,
            posting_reference=obj.declaration_number,
            notes=obj.notes,
            income_date=obj.receipt_date,
            actor=actor,
        )
        income = result["income"]
        obj.confirmed_account = account
        obj.finance_confirmed_by = actor
        obj.finance_confirmed_at = timezone.now()
        obj.finance_comment = (comment or "").strip()
        obj.posted_income = income
        obj.status = "FINANCE_CONFIRMED"
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def return_or_reject(cls, declaration, actor, decision, comment=""):
        obj = cls._lock(declaration)
        cls._prevent_self_approval(obj, actor)
        if decision not in {"RETURNED", "REJECTED"} or not (comment or "").strip():
            raise ValidationError("A valid decision and reason are required.")
        if obj.status == "SUBMITTED":
            cls._require_group(actor, "Manager", "Construction Manager", "Furniture Manager", "Marketplace Manager", "Finance Manager")
            obj.unit_comment = comment
        elif obj.status == "UNIT_APPROVED":
            cls._require_group(actor, "Accountant", "Finance Manager")
            obj.finance_comment = comment
        else:
            raise ValidationError("This declaration cannot be returned or rejected now.")
        obj.status = decision
        obj.save()
        return obj
