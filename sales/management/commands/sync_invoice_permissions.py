from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "Sales Officer": {
        "view_enterpriseinvoice", "add_enterpriseinvoice",
        "change_enterpriseinvoice", "issue_enterpriseinvoice",
        "send_enterpriseinvoice", "view_invoicedelivery",
    },
    "Manager": {"view_enterpriseinvoice", "view_invoicedelivery"},
    "Finance Manager": {"view_enterpriseinvoice", "view_invoicedelivery"},
    "Accountant": {"view_enterpriseinvoice", "view_invoicedelivery"},
    "CEO": {
        "view_enterpriseinvoice", "add_enterpriseinvoice",
        "change_enterpriseinvoice", "delete_enterpriseinvoice",
        "issue_enterpriseinvoice", "send_enterpriseinvoice",
        "void_enterpriseinvoice", "view_invoicedelivery",
    },
    "Administrator": {
        "view_enterpriseinvoice", "add_enterpriseinvoice",
        "change_enterpriseinvoice", "delete_enterpriseinvoice",
        "issue_enterpriseinvoice", "send_enterpriseinvoice",
        "void_enterpriseinvoice", "view_invoicedelivery",
        "change_invoicedelivery", "delete_invoicedelivery",
    },
}


class Command(BaseCommand):
    help = "Synchronize Enterprise Invoice permissions into Django groups."

    def handle(self, *args, **options):
        available = {
            permission.codename: permission
            for permission in Permission.objects.filter(
                content_type__app_label="sales",
                codename__in=set().union(*ROLE_PERMISSIONS.values()),
            )
        }
        missing = set().union(*ROLE_PERMISSIONS.values()) - set(available)
        if missing:
            self.stderr.write(self.style.ERROR(
                "Missing permissions (run migrate first): " + ", ".join(sorted(missing))
            ))
            return
        for group_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            group.permissions.add(*(available[name] for name in codenames))
            self.stdout.write(f"{group_name}: {len(codenames)} invoice permissions")
        self.stdout.write(self.style.SUCCESS("Invoice group permissions synchronized."))
