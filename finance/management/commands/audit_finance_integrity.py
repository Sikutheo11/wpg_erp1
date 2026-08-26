from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Sum

from finance.models import Account, Expense, Income, Transaction


ZERO = Decimal("0.00")


class Command(BaseCommand):
    help = (
        "Audit Finance balances, ledger links and posting integrity without "
        "changing any data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-errors",
            action="store_true",
            help="Return a non-zero exit status when integrity errors exist.",
        )

    def handle(self, *args, **options):
        errors = []
        warnings = []

        self._check_amounts(errors)
        self._check_income_links(errors, warnings)
        self._check_expense_links(errors, warnings)
        self._check_managed_transactions(errors)

        self.stdout.write("=== FINANCE ACCOUNT LEDGER SUMMARY ===")
        for account in Account.objects.order_by("pk"):
            totals = account.transactions.aggregate(
                incoming=Sum(
                    "amount",
                    filter=Q(transaction_type="income"),
                    default=ZERO,
                ),
                outgoing=Sum(
                    "amount",
                    filter=Q(transaction_type="expense"),
                    default=ZERO,
                ),
            )
            incoming = totals["incoming"] or ZERO
            outgoing = totals["outgoing"] or ZERO
            inferred_opening = account.balance - incoming + outgoing
            self.stdout.write(
                " | ".join(
                    (
                        f"id={account.pk}",
                        f"account={account.name}",
                        f"balance={account.balance}",
                        f"ledger_in={incoming}",
                        f"ledger_out={outgoing}",
                        f"inferred_opening={inferred_opening}",
                    )
                )
            )
            if account.balance < ZERO:
                warnings.append(
                    f"Account {account.pk} ({account.name}) has a negative balance."
                )

        self.stdout.write("\n=== WARNINGS ===")
        if warnings:
            for message in warnings:
                self.stdout.write(self.style.WARNING(f"WARNING: {message}"))
        else:
            self.stdout.write("No warnings.")

        self.stdout.write("\n=== ERRORS ===")
        if errors:
            for message in errors:
                self.stdout.write(self.style.ERROR(f"ERROR: {message}"))
        else:
            self.stdout.write(self.style.SUCCESS("No integrity errors."))

        self.stdout.write(
            "\n"
            f"FINANCE_INTEGRITY_SUMMARY: errors={len(errors)} "
            f"warnings={len(warnings)}"
        )

        if errors and options["fail_on_errors"]:
            raise CommandError(
                f"Finance integrity audit failed with {len(errors)} error(s)."
            )

    @staticmethod
    def _check_amounts(errors):
        checks = (
            (Income, "Income"),
            (Expense, "Expense"),
            (Transaction, "Transaction"),
        )
        for model, label in checks:
            invalid_ids = list(
                model.objects.filter(amount__lte=ZERO)
                .order_by("pk")
                .values_list("pk", flat=True)[:25]
            )
            if invalid_ids:
                errors.append(
                    f"{label} records have non-positive amounts; ids={invalid_ids}."
                )

    @staticmethod
    def _check_income_links(errors, warnings):
        unlinked = Income.objects.filter(ledger_transaction__isnull=True).count()
        if unlinked:
            warnings.append(
                f"{unlinked} Income record(s) have no linked ledger transaction. "
                "These may be legacy or intentionally unposted records."
            )

        for income in Income.objects.exclude(
            ledger_transaction__isnull=True
        ).select_related("ledger_transaction"):
            ledger = income.ledger_transaction
            mismatches = []
            if ledger.account_id != income.account_id:
                mismatches.append("account")
            if ledger.transaction_type != "income":
                mismatches.append("direction")
            if ledger.amount != income.amount:
                mismatches.append("amount")
            if ledger.date != income.date:
                mismatches.append("date")
            expected_key = f"finance-income:{income.pk}"
            if ledger.posting_key != expected_key:
                mismatches.append("posting_key")
            if mismatches:
                errors.append(
                    f"Income {income.pk} ledger mismatch: {', '.join(mismatches)}."
                )

    @staticmethod
    def _check_expense_links(errors, warnings):
        unlinked = Expense.objects.filter(ledger_transaction__isnull=True).count()
        if unlinked:
            warnings.append(
                f"{unlinked} Expense record(s) have no linked ledger transaction. "
                "These may be legacy or intentionally unposted records."
            )

        for expense in Expense.objects.exclude(
            ledger_transaction__isnull=True
        ).select_related("ledger_transaction"):
            ledger = expense.ledger_transaction
            mismatches = []
            if ledger.account_id != expense.account_id:
                mismatches.append("account")
            if ledger.transaction_type != "expense":
                mismatches.append("direction")
            if ledger.amount != expense.amount:
                mismatches.append("amount")
            if ledger.date != expense.date:
                mismatches.append("date")
            expected_key = f"finance-expense:{expense.pk}"
            if ledger.posting_key != expected_key:
                mismatches.append("posting_key")
            if mismatches:
                errors.append(
                    f"Expense {expense.pk} ledger mismatch: {', '.join(mismatches)}."
                )

    @staticmethod
    def _check_managed_transactions(errors):
        managed = Transaction.objects.filter(posting_key__isnull=False)
        for ledger in managed:
            if ledger.posting_key.startswith("finance-income:"):
                linked = hasattr(ledger, "income_record")
            elif ledger.posting_key.startswith("finance-expense:"):
                linked = hasattr(ledger, "expense_record")
            else:
                linked = True
            if not linked:
                errors.append(
                    f"Managed Transaction {ledger.pk} ({ledger.posting_key}) is orphaned."
                )
