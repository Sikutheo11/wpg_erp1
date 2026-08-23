from django.db import migrations


FEATURES = {
    "MARKETPLACE_DASHBOARD": ("Dashboard", "ecommerce:ecommerce_dashboard", 1, {"view_permission": "ecommerce.view_onlineproduct"}),
    "MARKETPLACE_PRODUCTS": ("Online Products", "ecommerce:online_product_list", 3, {"view_permission": "ecommerce.view_onlineproduct", "add_permission": "ecommerce.add_onlineproduct", "change_permission": "ecommerce.change_onlineproduct", "delete_permission": "ecommerce.delete_onlineproduct"}),
    "MARKETPLACE_ORDERS": ("Online Orders", "", 4, {"view_permission": "ecommerce.view_ecommercecheckout", "add_permission": "ecommerce.add_ecommercecheckout", "change_permission": "ecommerce.change_ecommercecheckout", "delete_permission": "ecommerce.delete_ecommercecheckout"}),
    "MARKETPLACE_SELLERS": ("Sellers", "ecommerce:marketplace_seller_list", 5, {"view_permission": "ecommerce.view_marketplaceseller", "add_permission": "ecommerce.add_marketplaceseller", "change_permission": "ecommerce.change_marketplaceseller", "delete_permission": "ecommerce.delete_marketplaceseller"}),
    "MARKETPLACE_COMMISSIONS": ("Commissions", "ecommerce:marketplace_seller_list", 6, {"view_permission": "ecommerce.view_sellerproductassignment", "add_permission": "ecommerce.add_sellerproductassignment", "change_permission": "ecommerce.change_sellerproductassignment", "delete_permission": "ecommerce.delete_sellerproductassignment"}),
    "MARKETPLACE_SETTLEMENTS": ("Settlements", "ecommerce:seller_settlement_list", 7, {"view_permission": "ecommerce.view_sellersettlement", "add_permission": "ecommerce.add_sellersettlement", "change_permission": "ecommerce.change_sellersettlement", "delete_permission": "ecommerce.delete_sellersettlement", "approve_permission": "ecommerce.approve_sellersettlement"}),
    "MARKETPLACE_PAYMENTS": ("Payments", "ecommerce:payment_list", 8, {"view_permission": "ecommerce.view_ecommercepayment", "add_permission": "ecommerce.add_ecommercepayment", "change_permission": "ecommerce.change_ecommercepayment", "delete_permission": "ecommerce.delete_ecommercepayment"}),
    "MARKETPLACE_REPORTS": ("Reports", "ecommerce:marketplace_report", 9, {"view_permission": "ecommerce.view_marketplaceorderline"}),
    "MARKETPLACE_PAYMENT_CONFIRM": ("Confirm Payment", "", 201, {"approve_permission": "ecommerce.confirm_ecommercepayment"}),
    "MARKETPLACE_PAYMENT_REFUND": ("Refund Payment", "", 202, {"approve_permission": "ecommerce.refund_ecommercepayment"}),
    "MARKETPLACE_SETTLEMENT_PAY": ("Pay Settlement", "", 203, {"approve_permission": "ecommerce.pay_sellersettlement"}),
}


INHERIT_FROM = {
    "MARKETPLACE_SELLERS": ("MARKETPLACE_PRODUCTS",),
    "MARKETPLACE_COMMISSIONS": ("MARKETPLACE_PRODUCTS",),
    "MARKETPLACE_SETTLEMENTS": ("MARKETPLACE_ORDERS",),
    "MARKETPLACE_PAYMENTS": ("MARKETPLACE_ORDERS",),
    "MARKETPLACE_REPORTS": ("MARKETPLACE_DASHBOARD",),
    "MARKETPLACE_PAYMENT_CONFIRM": ("MARKETPLACE_PAYMENTS",),
    "MARKETPLACE_PAYMENT_REFUND": ("MARKETPLACE_PAYMENTS",),
    "MARKETPLACE_SETTLEMENT_PAY": ("MARKETPLACE_SETTLEMENTS",),
}


def find_permission(Permission, name):
    app_label, codename = name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()


def configure_ecommerce_permissions(apps, schema_editor):
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    business_unit, _ = BusinessUnit.objects.get_or_create(
        code="MARKETPLACE",
        defaults={
            "name": "Marketplace",
            "description": "WPG Ecommerce and Marketplace.",
            "icon": "bi bi-shop",
            "order": 4,
            "is_active": True,
        },
    )

    custom_permissions = (
        ("ecommercepayment", "confirm_ecommercepayment", "Can confirm ecommerce payments"),
        ("ecommercepayment", "refund_ecommercepayment", "Can refund ecommerce payments"),
        ("sellersettlement", "approve_sellersettlement", "Can approve or cancel seller settlements"),
        ("sellersettlement", "pay_sellersettlement", "Can pay seller settlements"),
    )
    for model, codename, name in custom_permissions:
        content_type, _ = ContentType.objects.get_or_create(
            app_label="ecommerce",
            model=model,
        )
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )

    for code, (name, url_name, order, permissions) in FEATURES.items():
        Feature.objects.update_or_create(
            code=code,
            defaults={
                "business_unit": business_unit,
                "engine": None,
                "name": name,
                "url_name": url_name,
                "icon": "bi bi-shop",
                "order": order,
                "is_active": True,
                **permissions,
            },
        )

    actions = (
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
        for legacy_field, feature_field in actions:
            if not getattr(role_feature, legacy_field):
                continue
            name = getattr(role_feature.feature, feature_field, "").strip()
            permission = find_permission(Permission, name) if name else None
            if permission:
                Group.objects.get(pk=role_feature.role_id).permissions.add(permission.pk)

    for target_code, source_codes in INHERIT_FROM.items():
        target = Feature.objects.get(code=target_code)
        for legacy_field, feature_field in actions:
            name = getattr(target, feature_field, "").strip()
            permission = find_permission(Permission, name) if name else None
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
        ("core", "0020_configure_furniture_permissions"),
        ("ecommerce", "0011_add_marketplace_workflow_permissions"),
    ]

    operations = [
        migrations.RunPython(
            configure_ecommerce_permissions,
            migrations.RunPython.noop,
        ),
    ]
