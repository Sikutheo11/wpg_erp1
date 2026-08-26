from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from Employee.models import Department
from finance.models import (
    Account,
    Counterparty,
    ExpenseRequest,
    IncomeDeclaration,
    Transaction,
)
from finance.services.expense_request_service import ExpenseRequestService
from finance.services.income_declaration_service import IncomeDeclarationService


class ExpenseRequestWorkflowTests(TestCase):
    @staticmethod
    def user(username, group):
        user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            first_name=username.title(),
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        return user

    def setUp(self):
        self.requester = self.user("requester", "Worker")
        self.manager = self.user("line-manager", "Manager")
        self.accountant = self.user("accountant", "Accountant")
        self.finance_manager = self.user("finance-manager", "Finance Manager")
        self.director = self.user("director", "CEO")
        self.department, _ = Department.objects.get_or_create(name="operations", defaults={"manager": self.manager})
        if self.department.manager_id != self.manager.pk:
            self.department.manager = self.manager
            self.department.save(update_fields=["manager"])
        self.payee = Counterparty.objects.create(name="Example Payee", phone="0788111222")
        self.account = Account.objects.create(name="Main Cash", account_type="cash", balance=Decimal("500000"))
        self.request = ExpenseRequest.objects.create(
            requested_by=self.requester,
            department=self.department,
            business_unit="SHARED",
            request_type="DIRECT_PAYMENT",
            title="Workshop transport",
            expense_type="transport",
            purpose="Move finished furniture to the customer.",
            payee=self.payee,
            amount_requested=Decimal("100000"),
            needed_by=timezone.localdate() + timedelta(days=2),
        )

    def test_full_approval_and_payment_posts_expense_once(self):
        ExpenseRequestService.submit(self.request, self.requester)
        ExpenseRequestService.manager_approve(self.request, self.manager, "Needed")
        ExpenseRequestService.accountant_verify(self.request, self.accountant, self.account, True, "Funds available")
        ExpenseRequestService.finance_approve(self.request, self.finance_manager, "Cash flow checked")
        ExpenseRequestService.director_approve(self.request, self.director, "Priority approved")
        ExpenseRequestService.pay(self.request, self.accountant, self.account, Decimal("100000"), "cash", "PV-001")

        self.request.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(self.request.status, "COMPLETED")
        self.assertEqual(self.request.expense.paid_to, self.payee)
        self.assertIsNotNone(self.request.expense.ledger_transaction_id)
        self.assertEqual(
            self.request.expense.ledger_transaction.posting_key,
            f"finance-expense:{self.request.expense_id}",
        )
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.account.balance, Decimal("400000"))

    def test_requester_cannot_approve_own_request(self):
        self.requester.groups.add(Group.objects.get_or_create(name="Manager")[0])
        ExpenseRequestService.submit(self.request, self.requester)
        with self.assertRaises(PermissionDenied):
            ExpenseRequestService.manager_approve(self.request, self.requester)

    def test_submitted_request_only_shows_manager_actions_to_assigned_line_manager(self):
        view_permission = Permission.objects.get(
            content_type__app_label="finance",
            codename="view_expenserequest",
        )
        change_permission = Permission.objects.get(
            content_type__app_label="finance",
            codename="change_expenserequest",
        )
        for user in (
            self.requester,
            self.manager,
            self.accountant,
            self.finance_manager,
            self.director,
        ):
            user.user_permissions.add(view_permission, change_permission)

        ExpenseRequestService.submit(self.request, self.requester)
        url = f"/finance/expense-requests/{self.request.pk}/"

        for user in (self.requester, self.accountant, self.finance_manager, self.director):
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Manager Approve")
            self.assertNotContains(response, "Return for Correction")
            self.assertNotContains(response, "Reject")

        self.client.force_login(self.manager)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manager Approve")
        self.assertContains(response, "Return for Correction")
        self.assertContains(response, "Reject")

    def test_accountant_cannot_verify_without_enough_funds(self):
        self.account.balance = Decimal("10")
        self.account.save(update_fields=["balance"])
        ExpenseRequestService.submit(self.request, self.requester)
        ExpenseRequestService.manager_approve(self.request, self.manager)
        with self.assertRaises(ValidationError):
            ExpenseRequestService.accountant_verify(self.request, self.accountant, self.account, True)

    def test_payment_requires_final_approval(self):
        with self.assertRaises(ValidationError):
            ExpenseRequestService.pay(self.request, self.accountant, self.account, Decimal("100000"), "cash", "PV-002")

    def test_request_cannot_submit_without_department_and_matching_business_unit(self):
        self.request.department = None
        self.request.save(update_fields=["department"])
        with self.assertRaises(ValidationError):
            ExpenseRequestService.submit(self.request, self.requester)

        self.request.department = self.department
        self.request.business_unit = "FURNITURE"
        self.request.save(update_fields=["department", "business_unit"])
        with self.assertRaises(ValidationError):
            ExpenseRequestService.submit(self.request, self.requester)

    def test_cash_advance_waits_for_accountability(self):
        self.request.request_type = "CASH_ADVANCE"
        self.request.payee = None
        self.request.save()
        ExpenseRequestService.submit(self.request, self.requester)
        ExpenseRequestService.manager_approve(self.request, self.manager)
        ExpenseRequestService.accountant_verify(self.request, self.accountant, self.account, True)
        ExpenseRequestService.finance_approve(self.request, self.finance_manager)
        ExpenseRequestService.director_approve(self.request, self.director)
        ExpenseRequestService.pay(self.request, self.accountant, self.account, Decimal("100000"), "cash", "ADV-001")
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "ACCOUNTABILITY_PENDING")


class IncomeDeclarationWorkflowTests(TestCase):
    @staticmethod
    def user(username, group):
        user = get_user_model().objects.create_user(
            username=username, email=f"{username}@example.com",
            first_name=username.title(), last_name="Tester",
            password="Strong-Test-Password-2026",
        )
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        return user

    def setUp(self):
        self.recorder = self.user("income-recorder", "Worker")
        self.manager = self.user("income-manager", "Manager")
        self.accountant = self.user("income-accountant", "Accountant")
        self.department, _ = Department.objects.get_or_create(
            name="sales",
            defaults={"manager": self.manager, "business_unit": "AGRICULTURE"},
        )
        if self.department.manager_id != self.manager.pk:
            self.department.manager = self.manager
        self.department.business_unit = "AGRICULTURE"
        self.department.save(update_fields=["manager", "business_unit"])
        self.account = Account.objects.create(name="WPG Bank", account_type="bank", balance=Decimal("200000"))
        self.payer = Counterparty.objects.create(name="Grant Partner", phone="0788333444")
        self.declaration = IncomeDeclaration.objects.create(
            recorded_by=self.recorder, department=self.department,
            business_unit="AGRICULTURE", title="Poultry programme grant",
            source_type="GRANT", amount=Decimal("300000"),
            received_from=self.payer, receipt_method="bank",
            receipt_date=timezone.localdate(), reference="BANK-IR-001",
        )

    def test_unit_income_is_not_posted_before_finance_confirmation(self):
        IncomeDeclarationService.submit(self.declaration, self.recorder)
        IncomeDeclarationService.unit_approve(self.declaration, self.manager)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("200000"))
        IncomeDeclarationService.finance_confirm(self.declaration, self.accountant, self.account, "Matched bank statement")
        self.declaration.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(self.declaration.status, "FINANCE_CONFIRMED")
        self.assertEqual(self.declaration.posted_income.business_unit, "AGRICULTURE")
        self.assertIsNotNone(
            self.declaration.posted_income.ledger_transaction_id
        )
        self.assertEqual(
            self.declaration.posted_income.ledger_transaction.posting_key,
            f"finance-income:{self.declaration.posted_income_id}",
        )
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.account.balance, Decimal("500000"))

    def test_recorder_cannot_confirm_own_income(self):
        self.recorder.groups.add(Group.objects.get_or_create(name="Accountant")[0])
        IncomeDeclarationService.submit(self.declaration, self.recorder)
        IncomeDeclarationService.unit_approve(self.declaration, self.manager)
        with self.assertRaises(PermissionDenied):
            IncomeDeclarationService.finance_confirm(self.declaration, self.recorder, self.account)

    def test_income_business_unit_must_match_department(self):
        self.declaration.business_unit = "CONSTRUCTION"
        self.declaration.save(update_fields=["business_unit"])
        with self.assertRaises(ValidationError):
            IncomeDeclarationService.submit(self.declaration, self.recorder)

    def test_submitted_income_only_shows_unit_action_to_assigned_manager(self):
        view_permission = Permission.objects.get(
            content_type__app_label="finance",
            codename="view_incomedeclaration",
        )
        change_permission = Permission.objects.get(
            content_type__app_label="finance",
            codename="change_incomedeclaration",
        )
        for user in (self.recorder, self.manager, self.accountant):
            user.user_permissions.add(view_permission, change_permission)

        finance_manager = self.user("income-finance-manager", "Finance Manager")
        finance_manager.user_permissions.add(view_permission, change_permission)
        IncomeDeclarationService.submit(self.declaration, self.recorder)
        url = f"/finance/income-declarations/{self.declaration.pk}/"

        for user in (self.recorder, self.accountant, finance_manager):
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Confirm Business Source")

        self.client.force_login(self.manager)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm Business Source")

    def test_income_submit_redirects_to_income_declaration_detail(self):
        add_permission = Permission.objects.get(
            content_type__app_label="finance",
            codename="add_incomedeclaration",
        )
        self.recorder.user_permissions.add(add_permission)
        self.client.force_login(self.recorder)
        response = self.client.post(
            f"/finance/income-declarations/{self.declaration.pk}/submit/"
        )
        self.assertRedirects(
            response,
            f"/finance/income-declarations/{self.declaration.pk}/",
            fetch_redirect_response=False,
        )
