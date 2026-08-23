from django.db import migrations


FEATURES = {
    "FINANCE_DASHBOARD": ("FINANCE", "Dashboard", "finance:finance_dashboard", "bi bi-speedometer2", 1, {"view_permission": "finance.view_account"}),
    "FINANCE_ACCOUNTS": ("FINANCE", "Accounts", "finance:account_list", "bi bi-bank", 2, {"view_permission": "finance.view_account", "add_permission": "finance.add_account", "change_permission": "finance.change_account", "delete_permission": "finance.delete_account"}),
    "FINANCE_INCOME": ("FINANCE", "Income", "finance:income_list", "bi bi-arrow-down-circle", 3, {"view_permission": "finance.view_income", "add_permission": "finance.add_income", "change_permission": "finance.change_income", "delete_permission": "finance.delete_income"}),
    "FINANCE_EXPENSES": ("FINANCE", "Expenses", "finance:expense_list", "bi bi-arrow-up-circle", 4, {"view_permission": "finance.view_expense", "add_permission": "finance.add_expense", "change_permission": "finance.change_expense", "delete_permission": "finance.delete_expense"}),
    "FINANCE_PAYMENTS": ("FINANCE", "Payments", "finance:payment_list", "bi bi-cash", 5, {"view_permission": "finance.view_payment", "add_permission": "finance.add_payment", "change_permission": "finance.change_payment", "delete_permission": "finance.delete_payment"}),
    "FINANCE_RECEIVABLES": ("FINANCE", "Receivables", "finance:receivable_list", "bi bi-wallet2", 6, {"view_permission": "finance.view_receivable", "add_permission": "finance.add_receivable", "change_permission": "finance.change_receivable", "delete_permission": "finance.delete_receivable"}),
    "FINANCE_PAYABLES": ("FINANCE", "Payables", "finance:payable_list", "bi bi-receipt", 7, {"view_permission": "finance.view_payable", "add_permission": "finance.add_payable", "change_permission": "finance.change_payable", "delete_permission": "finance.delete_payable"}),
    "FINANCE_COUNTERPARTIES": ("FINANCE", "People & Companies", "finance:counterparty_phone_lookup", "bi bi-person-vcard", 8, {"view_permission": "finance.view_counterparty", "add_permission": "finance.add_counterparty", "change_permission": "finance.change_counterparty", "delete_permission": "finance.delete_counterparty"}),
    "FINANCE_DEBTS": ("FINANCE", "Debts", "finance:debt_list", "bi bi-journal-text", 9, {"view_permission": "finance.view_debtrecord", "add_permission": "finance.add_debtrecord", "change_permission": "finance.change_debtrecord", "delete_permission": "finance.delete_debtrecord"}),
    "FINANCE_PAYROLL": ("FINANCE", "Payroll", "finance:payroll_list", "bi bi-people", 10, {"view_permission": "finance.view_payroll", "add_permission": "finance.add_payroll", "change_permission": "finance.change_payroll", "delete_permission": "finance.delete_payroll"}),
    "FINANCE_REPORTS": ("FINANCE", "Financial Reports", "finance:financial_report", "bi bi-bar-chart", 11, {"view_permission": "finance.view_transaction"}),
    "PEOPLE_DASHBOARD": ("PEOPLE", "Dashboard", "employee:employee_dashboard", "bi bi-speedometer2", 1, {"view_permission": "Employee.view_employee"}),
    "PEOPLE_EMPLOYEES": ("PEOPLE", "Employees", "employee:employee_list", "bi bi-person-badge", 2, {"view_permission": "Employee.view_employee", "add_permission": "Employee.add_employee", "change_permission": "Employee.change_employee", "delete_permission": "Employee.delete_employee"}),
    "PEOPLE_DEPARTMENTS": ("PEOPLE", "Departments", "employee:department_list", "bi bi-diagram-3", 3, {"view_permission": "Employee.view_department", "add_permission": "Employee.add_department", "change_permission": "Employee.change_department", "delete_permission": "Employee.delete_department"}),
    "PEOPLE_ATTENDANCE": ("PEOPLE", "Attendance", "employee:attendance_list", "bi bi-calendar-check", 4, {"view_permission": "Employee.view_attendance", "add_permission": "Employee.add_attendance", "change_permission": "Employee.change_attendance", "delete_permission": "Employee.delete_attendance"}),
    "PEOPLE_LEAVE": ("PEOPLE", "Leave", "employee:leave_list", "bi bi-calendar2-week", 5, {"view_permission": "Employee.view_leave", "add_permission": "Employee.add_leave", "change_permission": "Employee.change_leave", "delete_permission": "Employee.delete_leave"}),
    "PEOPLE_POSITIONS": ("PEOPLE", "Positions", "employee:position_list", "bi bi-person-workspace", 6, {"view_permission": "Employee.view_position", "add_permission": "Employee.add_position", "change_permission": "Employee.change_position", "delete_permission": "Employee.delete_position"}),
    "PEOPLE_CONTACTS": ("PEOPLE", "Contacts", "employee:contact_list", "bi bi-person-lines-fill", 7, {"view_permission": "Employee.view_contact", "add_permission": "Employee.add_contact", "change_permission": "Employee.change_contact", "delete_permission": "Employee.delete_contact"}),
    "PEOPLE_REPORTS": ("PEOPLE", "People Reports", "employee:employee_report", "bi bi-file-bar-graph", 8, {"view_permission": "Employee.view_employee"}),
}


INHERIT_FROM = {
    "FINANCE_COUNTERPARTIES": ("FINANCE_RECEIVABLES", "FINANCE_PAYABLES"),
    "FINANCE_DEBTS": ("FINANCE_RECEIVABLES", "FINANCE_PAYABLES"),
    "FINANCE_PAYROLL": ("FINANCE_DASHBOARD",),
    "FINANCE_REPORTS": ("FINANCE_DASHBOARD",),
    "PEOPLE_POSITIONS": ("PEOPLE_DEPARTMENTS",),
    "PEOPLE_CONTACTS": ("PEOPLE_EMPLOYEES",),
    "PEOPLE_REPORTS": ("PEOPLE_EMPLOYEES",),
}


def _find_permission(Permission, permission_name):
    app_label, codename = permission_name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label__iexact=app_label,
        codename=codename,
    ).first()


def configure_permissions(apps, schema_editor):
    EnterpriseEngine = apps.get_model("core", "EnterpriseEngine")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    for code, (engine_code, name, url_name, icon, order, permissions) in FEATURES.items():
        engine = EnterpriseEngine.objects.filter(code=engine_code).first()
        if not engine:
            continue
        defaults = {
            "engine": engine,
            "business_unit": None,
            "name": name,
            "url_name": url_name,
            "icon": icon,
            "order": order,
            "is_active": True,
            **permissions,
        }
        Feature.objects.update_or_create(code=code, defaults=defaults)

    action_fields = (
        ("can_view", "view_permission"),
        ("can_add", "add_permission"),
        ("can_edit", "change_permission"),
        ("can_delete", "delete_permission"),
        ("can_approve", "approve_permission"),
    )
    relevant_codes = tuple(FEATURES)
    role_features = RoleFeature.objects.filter(
        feature__code__in=relevant_codes,
    ).select_related("role", "feature")
    for role_feature in role_features.iterator():
        permission_ids = []
        for legacy_field, feature_field in action_fields:
            if not getattr(role_feature, legacy_field):
                continue
            permission_name = getattr(role_feature.feature, feature_field, "").strip()
            if permission_name:
                permission = _find_permission(Permission, permission_name)
                if permission:
                    permission_ids.append(permission.pk)
        if permission_ids:
            Group.objects.get(pk=role_feature.role_id).permissions.add(*permission_ids)

    # New menu entries inherit access from the closest legacy feature. This
    # preserves existing roles while future roles use Django permissions only.
    inherited_actions = (
        ("can_view", "view_permission"),
        ("can_add", "add_permission"),
        ("can_edit", "change_permission"),
        ("can_delete", "delete_permission"),
    )
    for target_code, source_codes in INHERIT_FROM.items():
        target = Feature.objects.filter(code=target_code).first()
        if not target:
            continue
        for legacy_field, feature_field in inherited_actions:
            permission_name = getattr(target, feature_field, "").strip()
            permission = (
                _find_permission(Permission, permission_name)
                if permission_name
                else None
            )
            if not permission:
                continue
            group_ids = RoleFeature.objects.filter(
                feature__code__in=source_codes,
                **{legacy_field: True},
            ).values_list("role_id", flat=True).distinct()
            for group in Group.objects.filter(pk__in=group_ids):
                group.permissions.add(permission.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_feature_django_permissions"),
        ("Employee", "0012_alter_leave_options"),
        ("finance", "0008_support_debt_raw_materials_and_assets"),
    ]

    operations = [
        migrations.RunPython(
            configure_permissions,
            migrations.RunPython.noop,
        ),
    ]
