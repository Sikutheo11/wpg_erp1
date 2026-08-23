from django.db import migrations


FEATURES = {
    "CUSTOMER_LIST": ("CUSTOMER", "Customers", "sales:customer_list", "bi bi-people", 1, {"view_permission": "sales.view_customer", "add_permission": "sales.add_customer", "change_permission": "sales.change_customer", "delete_permission": "sales.delete_customer"}),
    "CUSTOMER_HISTORY": ("CUSTOMER", "Customer History", "sales:customer_list", "bi bi-clock-history", 2, {"view_permission": "sales.view_customer"}),
    "ORDER_LIST": ("ORDER", "All Orders", "orders:order_list", "bi bi-list-ul", 1, {"view_permission": "orders.view_order", "add_permission": "orders.add_order", "change_permission": "orders.change_order", "delete_permission": "orders.delete_order"}),
    "ORDER_RESTOCK": ("ORDER", "Restock Orders", "orders:business_unit_select", "bi bi-arrow-repeat", 2, {"view_permission": "orders.view_order", "add_permission": "orders.add_order"}),
    "ORDER_APPROVAL": ("ORDER", "Order Approval", "orders:order_list", "bi bi-check-circle", 3, {"view_permission": "orders.view_order", "approve_permission": "orders.approve_order"}),
    "ORDER_FULFILMENT": ("ORDER", "Order Fulfilment", "orders:order_list", "bi bi-truck", 4, {"view_permission": "orders.view_order", "approve_permission": "orders.fulfil_order"}),
    "SALES_DASHBOARD": ("ORDER", "Sales Dashboard", "sales:sales_dashboard", "bi bi-speedometer2", 5, {"view_permission": "sales.view_sale"}),
    "SALES_LIST": ("ORDER", "Sales", "sales:sale_list", "bi bi-receipt", 6, {"view_permission": "sales.view_sale", "add_permission": "sales.add_sale", "change_permission": "sales.change_sale", "delete_permission": "sales.delete_sale"}),
    "SALES_INVOICES": ("ORDER", "Invoices", "sales:invoice_list", "bi bi-file-earmark-text", 7, {"view_permission": "sales.view_invoice", "add_permission": "sales.add_invoice", "change_permission": "sales.change_invoice", "delete_permission": "sales.delete_invoice"}),
    "SALES_PAYMENTS": ("ORDER", "Customer Payments", "sales:payment_list", "bi bi-cash-coin", 8, {"view_permission": "sales.view_customerpayment", "add_permission": "sales.add_customerpayment", "change_permission": "sales.change_customerpayment", "delete_permission": "sales.delete_customerpayment"}),
    "SALES_REPORTS": ("ORDER", "Sales Reports", "sales:sales_report", "bi bi-bar-chart", 9, {"view_permission": "sales.view_sale"}),
    "QUOTATION_LIST": ("QUOTATION", "Quotations", "sales:quotation_list", "bi bi-file-earmark-text", 1, {"view_permission": "sales.view_salesquotation", "add_permission": "sales.add_salesquotation", "change_permission": "sales.change_salesquotation", "delete_permission": "sales.delete_salesquotation"}),
    "QUOTATION_APPROVAL": ("QUOTATION", "Quotation Approval", "sales:quotation_list", "bi bi-check-circle", 2, {"view_permission": "sales.view_salesquotation", "approve_permission": "sales.approve_salesquotation"}),
}


INHERIT_FROM = {
    "ORDER_APPROVAL": ("ORDER_LIST",),
    "ORDER_FULFILMENT": ("ORDER_LIST",),
    "SALES_DASHBOARD": ("ORDER_LIST",),
    "SALES_LIST": ("ORDER_LIST",),
    "SALES_INVOICES": ("ORDER_LIST",),
    "SALES_PAYMENTS": ("ORDER_LIST",),
    "SALES_REPORTS": ("ORDER_LIST",),
}


PHASE2_INHERIT_FROM = {
    "FINANCE_COUNTERPARTIES": ("FINANCE_RECEIVABLES", "FINANCE_PAYABLES"),
    "FINANCE_DEBTS": ("FINANCE_RECEIVABLES", "FINANCE_PAYABLES"),
    "FINANCE_PAYROLL": ("FINANCE_DASHBOARD",),
    "FINANCE_REPORTS": ("FINANCE_DASHBOARD",),
    "PEOPLE_POSITIONS": ("PEOPLE_DEPARTMENTS",),
    "PEOPLE_CONTACTS": ("PEOPLE_EMPLOYEES",),
    "PEOPLE_REPORTS": ("PEOPLE_EMPLOYEES",),
}


def _permission(Permission, name):
    app_label, codename = name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label__iexact=app_label,
        codename=codename,
    ).first()


def configure_features(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    EnterpriseEngine = apps.get_model("core", "EnterpriseEngine")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    # Phase 2 originally copied every target permission from can_view. Correct
    # databases that already ran that migration before its action-aware fix.
    corrective_actions = (
        ("can_add", "add_permission"),
        ("can_edit", "change_permission"),
        ("can_delete", "delete_permission"),
    )
    for target_code, source_codes in PHASE2_INHERIT_FROM.items():
        target = Feature.objects.filter(code=target_code).first()
        if not target:
            continue
        viewer_ids = set(
            RoleFeature.objects.filter(
                feature__code__in=source_codes,
                can_view=True,
            ).values_list("role_id", flat=True)
        )
        for legacy_field, feature_field in corrective_actions:
            name = getattr(target, feature_field, "").strip()
            permission = _permission(Permission, name) if name else None
            if not permission:
                continue
            entitled_ids = set(
                RoleFeature.objects.filter(
                    feature__code__in=source_codes,
                    **{legacy_field: True},
                ).values_list("role_id", flat=True)
            )
            target_entitled_ids = set(
                RoleFeature.objects.filter(
                    feature=target,
                    **{legacy_field: True},
                ).values_list("role_id", flat=True)
            )
            remove_ids = viewer_ids - entitled_ids - target_entitled_ids
            for group in Group.objects.filter(pk__in=remove_ids):
                group.permissions.remove(permission.pk)

    # Custom permissions must exist before legacy RoleFeature rows can be
    # transferred. Django's post_migrate will reuse these rows afterwards.
    custom_permissions = (
        ("sales", "salesquotation", "approve_salesquotation", "Can approve or reject sales quotations"),
        ("sales", "salesquotation", "convert_salesquotation", "Can convert sales quotations to orders"),
        ("orders", "order", "approve_order", "Can confirm or cancel enterprise orders"),
        ("orders", "order", "fulfil_order", "Can process and deliver enterprise orders"),
    )
    for app_label, model, codename, name in custom_permissions:
        content_type, _ = ContentType.objects.get_or_create(
            app_label=app_label,
            model=model,
        )
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )

    for code, (engine_code, name, url_name, icon, order, permissions) in FEATURES.items():
        engine = EnterpriseEngine.objects.filter(code=engine_code).first()
        if not engine:
            continue
        Feature.objects.update_or_create(
            code=code,
            defaults={
                "engine": engine,
                "business_unit": None,
                "name": name,
                "url_name": url_name,
                "icon": icon,
                "order": order,
                "is_active": True,
                **permissions,
            },
        )

    action_fields = (
        ("can_view", "view_permission"),
        ("can_add", "add_permission"),
        ("can_edit", "change_permission"),
        ("can_delete", "delete_permission"),
        ("can_approve", "approve_permission"),
    )
    role_features = RoleFeature.objects.filter(
        feature__code__in=tuple(FEATURES),
    ).select_related("role", "feature")
    for role_feature in role_features.iterator():
        permission_ids = []
        for legacy_field, feature_field in action_fields:
            if not getattr(role_feature, legacy_field):
                continue
            name = getattr(role_feature.feature, feature_field, "").strip()
            permission = _permission(Permission, name) if name else None
            if permission:
                permission_ids.append(permission.pk)
        if permission_ids:
            Group.objects.get(pk=role_feature.role_id).permissions.add(*permission_ids)

    inherited_actions = (
        ("can_view", "view_permission"),
        ("can_add", "add_permission"),
        ("can_edit", "change_permission"),
        ("can_delete", "delete_permission"),
        ("can_approve", "approve_permission"),
    )
    for target_code, source_codes in INHERIT_FROM.items():
        target = Feature.objects.filter(code=target_code).first()
        if not target:
            continue
        for legacy_field, feature_field in inherited_actions:
            name = getattr(target, feature_field, "").strip()
            permission = _permission(Permission, name) if name else None
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
        ("core", "0017_configure_finance_people_permissions"),
        ("sales", "0006_alter_salesquotation_options"),
        ("orders", "0005_alter_order_options"),
    ]

    operations = [
        migrations.RunPython(configure_features, migrations.RunPython.noop),
    ]
