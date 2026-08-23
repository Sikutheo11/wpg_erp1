from django.db import migrations


FEATURES = {
    "INVENTORY_DASHBOARD": ("Dashboard", "inventory:inventory_dashboard", 1, {"view_permission": "inventory.view_product"}),
    "INVENTORY_PRODUCTS": ("Products", "inventory:product_list", 2, {"view_permission": "inventory.view_product", "add_permission": "inventory.add_product", "change_permission": "inventory.change_product", "delete_permission": "inventory.delete_product"}),
    "INVENTORY_RAW_MATERIALS": ("Raw Materials", "inventory:material_list", 3, {"view_permission": "inventory.view_rawmaterial", "add_permission": "inventory.add_rawmaterial", "change_permission": "inventory.change_rawmaterial", "delete_permission": "inventory.delete_rawmaterial"}),
    "INVENTORY_STOCK_MOVEMENTS": ("Stock Movements", "inventory:movement_list", 4, {"view_permission": "inventory.view_stockmovement", "add_permission": "inventory.add_stockmovement", "change_permission": "inventory.change_stockmovement", "delete_permission": "inventory.delete_stockmovement"}),
    "INVENTORY_REPORTS": ("Inventory Reports", "core:inventory_report", 5, {"view_permission": "inventory.view_product"}),
    "ASSET_LIST": ("Assets", "inventory:asset_list", 6, {"view_permission": "inventory.view_asset", "add_permission": "inventory.add_asset", "change_permission": "inventory.change_asset", "delete_permission": "inventory.delete_asset"}),
    "ASSET_ASSIGNMENTS": ("Asset Assignments", "", 7, {"view_permission": "inventory.view_assetassignment", "add_permission": "inventory.add_assetassignment", "change_permission": "inventory.change_assetassignment", "delete_permission": "inventory.delete_assetassignment"}),
}


def find_permission(Permission, name):
    app_label, codename = name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()


def configure_inventory_permissions(apps, schema_editor):
    EnterpriseEngine = apps.get_model("core", "EnterpriseEngine")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    engine, _ = EnterpriseEngine.objects.get_or_create(
        code="INVENTORY",
        defaults={
            "name": "Inventory",
            "description": "Shared WPG inventory engine.",
            "icon": "bi bi-boxes",
            "order": 4,
            "is_active": True,
        },
    )

    for code, (name, url_name, order, permissions) in FEATURES.items():
        Feature.objects.update_or_create(
            code=code,
            defaults={
                "business_unit": None,
                "engine": engine,
                "name": name,
                "url_name": url_name,
                "icon": "bi bi-boxes",
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


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_secure_core_reports"),
        ("inventory", "0009_alter_category_options_alter_product_options_and_more"),
    ]

    operations = [
        migrations.RunPython(
            configure_inventory_permissions,
            migrations.RunPython.noop,
        ),
    ]
