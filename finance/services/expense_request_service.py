from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import Account, Expense, ExpenseRequest


class ExpenseRequestService:
    """State transitions and segregation-of-duties controls for cash requests."""

    @staticmethod
    def _lock(expense_request):
        return ExpenseRequest.objects.select_for_update().get(pk=expense_request.pk)

    @staticmethod
    def _prevent_self_approval(expense_request, actor):
        if actor and expense_request.requested_by_id == actor.pk:
            raise PermissionDenied("You cannot approve or pay your own expense request.")

    @staticmethod
    def _require_group(actor, *group_names):
        if actor.is_superuser:
            return
        if not actor.groups.filter(name__in=group_names).exists():
            raise PermissionDenied(f"This action requires one of these roles: {', '.join(group_names)}.")

    @classmethod
    @transaction.atomic
    def submit(cls, expense_request, actor):
        obj = cls._lock(expense_request)
        if obj.requested_by_id != actor.pk:
            raise PermissionDenied("Only the requester can submit this request.")
        if obj.status not in {"DRAFT", "RETURNED"}:
            raise ValidationError("Only a draft or returned request can be submitted.")
        if not obj.department_id:
            raise ValidationError("Your employee profile must belong to a department before submission.")
        if not obj.department.manager_id:
            raise ValidationError("The department must have an assigned manager before submission.")
        if obj.business_unit != obj.department.business_unit:
            raise ValidationError("The request business unit must match the requester's department.")
        obj.full_clean()
        obj.status = "SUBMITTED"
        obj.save(update_fields=["status", "updated_at"])
        return obj

    @classmethod
    @transaction.atomic
    def manager_approve(cls, expense_request, actor, comment=""):
        obj = cls._lock(expense_request)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "Manager", "Construction Manager", "Furniture Manager", "Finance Manager")
        if obj.status != "SUBMITTED":
            raise ValidationError("This request is not awaiting line-manager approval.")
        if obj.department_id and obj.department.manager_id and obj.department.manager_id != actor.pk and not actor.is_superuser:
            raise PermissionDenied("Only the requester's line manager can approve this request.")
        obj.status = "MANAGER_APPROVED"
        obj.manager_approved_by = actor
        obj.manager_approved_at = timezone.now()
        obj.manager_comment = (comment or "").strip()
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def accountant_verify(cls, expense_request, actor, account, funds_available, comment=""):
        obj = cls._lock(expense_request)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "Accountant")
        if obj.status != "MANAGER_APPROVED":
            raise ValidationError("This request is not awaiting accountant verification.")
        if not funds_available:
            raise ValidationError("Confirm that funds are available before forwarding the request.")
        account = Account.objects.select_for_update().get(pk=account.pk)
        if account.balance < obj.amount_requested:
            raise ValidationError("The selected account cannot cover the requested amount.")
        obj.proposed_account = account
        obj.funds_available = True
        obj.balance_checked = account.balance
        obj.accountant_verified_by = actor
        obj.accountant_verified_at = timezone.now()
        obj.accountant_comment = (comment or "").strip()
        obj.status = "FINANCE_VERIFIED"
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def finance_approve(cls, expense_request, actor, comment=""):
        obj = cls._lock(expense_request)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "Finance Manager")
        if obj.status != "FINANCE_VERIFIED":
            raise ValidationError("This request is not awaiting finance-manager approval.")
        obj.status = "FINANCE_APPROVED"
        obj.finance_approved_by = actor
        obj.finance_approved_at = timezone.now()
        obj.finance_comment = (comment or "").strip()
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def director_approve(cls, expense_request, actor, comment=""):
        obj = cls._lock(expense_request)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "CEO")
        if obj.status != "FINANCE_APPROVED":
            raise ValidationError("This request is not awaiting final approval.")
        obj.status = "FINAL_APPROVED"
        obj.director_approved_by = actor
        obj.director_approved_at = timezone.now()
        obj.director_comment = (comment or "").strip()
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def return_or_reject(cls, expense_request, actor, decision, comment=""):
        obj = cls._lock(expense_request)
        cls._prevent_self_approval(obj, actor)
        stage_roles = {
            "SUBMITTED": ("Manager", "Construction Manager", "Furniture Manager", "Finance Manager"),
            "MANAGER_APPROVED": ("Accountant",),
            "FINANCE_VERIFIED": ("Finance Manager",),
            "FINANCE_APPROVED": ("CEO",),
            "FINAL_APPROVED": ("Accountant",),
        }
        if obj.status in stage_roles:
            cls._require_group(actor, *stage_roles[obj.status])
        if obj.status in {"PAID", "ACCOUNTABILITY_PENDING", "COMPLETED", "CANCELLED"}:
            raise ValidationError("This request can no longer be returned or rejected.")
        if decision not in {"RETURNED", "REJECTED"}:
            raise ValidationError("Invalid decision.")
        if not (comment or "").strip():
            raise ValidationError("A reason is required.")
        previous_status = obj.status
        obj.status = decision
        # Keep one visible audit comment in the field belonging to the current stage.
        if previous_status == "SUBMITTED":
            obj.manager_comment = comment
        elif previous_status == "MANAGER_APPROVED":
            obj.accountant_comment = comment
        elif previous_status == "FINANCE_VERIFIED":
            obj.finance_comment = comment
        else:
            obj.director_comment = comment
        obj.save()
        return obj

    @classmethod
    @transaction.atomic
    def pay(cls, expense_request, actor, account, amount, method, reference, notes=""):
        obj = cls._lock(expense_request)
        cls._prevent_self_approval(obj, actor)
        cls._require_group(actor, "Accountant")
        if obj.status != "FINAL_APPROVED":
            raise ValidationError("Only a finally approved request can be paid.")
        if obj.expense_id:
            raise ValidationError("This request has already been posted as an expense.")
        if amount != obj.amount_requested:
            raise ValidationError("V1 requires payment of the exact approved amount.")
        account = Account.objects.select_for_update().get(pk=account.pk)
        if account.balance < amount:
            raise ValidationError("The selected account does not have enough funds.")
        expense = Expense.objects.create(
            account=account,
            business_unit=obj.business_unit,
            title=f"{obj.title} [{obj.request_number}]",
            expense_type=obj.expense_type,
            amount=amount,
            paid_to=obj.payee,
            reference=(reference or "").strip(),
            notes=(notes or obj.purpose).strip(),
            date=timezone.localdate(),
        )
        obj.expense = expense
        obj.paid_by = actor
        obj.paid_at = timezone.now()
        obj.amount_paid = amount
        obj.payment_method = method
        obj.payment_reference = (reference or "").strip()
        obj.status = "ACCOUNTABILITY_PENDING" if obj.request_type == "CASH_ADVANCE" else "COMPLETED"
        obj.save()
        return obj
