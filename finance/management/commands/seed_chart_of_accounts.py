from django.core.management.base import BaseCommand
from django.db import transaction

from finance.general_ledger_models import LedgerAccount


ACCOUNTS = (
    {
        "code": "1100",
        "name": "Cash",
        "account_type": LedgerAccount.ASSET,
        "normal_balance": LedgerAccount.DEBIT,
        "business_unit": "",
        "is_control_account": False,
    },
    {
        "code": "1110",
        "name": "Bank",
        "account_type": LedgerAccount.ASSET,
        "normal_balance": LedgerAccount.DEBIT,
        "business_unit": "",
        "is_control_account": False,
    },
    {
        "code": "1120",
        "name": "Mobile Money",
        "account_type": LedgerAccount.ASSET,
        "normal_balance": LedgerAccount.DEBIT,
        "business_unit": "",
        "is_control_account": False,
    },
    {
        "code": "2100",
        "name": "Customer Advances",
        "account_type": LedgerAccount.LIABILITY,
        "normal_balance": LedgerAccount.CREDIT,
        "business_unit": "",
        "is_control_account": True,
    },

        {
        "code": "2200",
        "name": "Marketplace Seller Payables",
        "account_type": LedgerAccount.LIABILITY,
        "normal_balance": LedgerAccount.CREDIT,
        "business_unit": "MARKETPLACE",
        "is_control_account": True,
    },
    
    {
        "code": "4100",
        "name": "Furniture Revenue",
        "account_type": LedgerAccount.REVENUE,
        "normal_balance": LedgerAccount.CREDIT,
        "business_unit": "FURNITURE",
        "is_control_account": False,
    },
    {
        "code": "4200",
        "name": "Agriculture Revenue",
        "account_type": LedgerAccount.REVENUE,
        "normal_balance": LedgerAccount.CREDIT,
        "business_unit": "AGRICULTURE",
        "is_control_account": False,
    },
    {
        "code": "4300",
        "name": "Construction Revenue",
        "account_type": LedgerAccount.REVENUE,
        "normal_balance": LedgerAccount.CREDIT,
        "business_unit": "CONSTRUCTION",
        "is_control_account": False,
    },
    {
        "code": "4400",
        "name": "Marketplace Commission Revenue",
        "account_type": LedgerAccount.REVENUE,
        "normal_balance": LedgerAccount.CREDIT,
        "business_unit": "MARKETPLACE",
        "is_control_account": False,
    },
)


class Command(BaseCommand):
    help = "Create or update the initial WPG General Ledger accounts."

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for definition in ACCOUNTS:
            code = definition["code"]
            defaults = {
                key: value
                for key, value in definition.items()
                if key != "code"
            }
            defaults.update(
                {
                    "currency": "RWF",
                    "is_active": True,
                }
            )

            account, created = LedgerAccount.objects.update_or_create(
                code=code,
                defaults=defaults,
            )
            account.full_clean()
            account.save()

            if created:
                created_count += 1
                action = "CREATED"
            else:
                updated_count += 1
                action = "UPDATED"

            self.stdout.write(
                f"{action}  {account.code}  {account.name}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Chart of Accounts seeded successfully: "
                    f"{created_count} created, "
                    f"{updated_count} updated."
                )
            )
        )
