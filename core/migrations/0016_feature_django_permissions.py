from django.db import migrations, models


def configure_feature_permissions(apps, schema_editor):
    Feature = apps.get_model("core", "Feature")
    permission_map = {
        "CONSTRUCTION_DASHBOARD": {"view_permission": "Construction.view_project"},
        "CONSTRUCTION_PROJECTS": {
            "view_permission": "Construction.view_project",
            "add_permission": "Construction.add_project",
            "change_permission": "Construction.change_project",
            "delete_permission": "Construction.delete_project",
        },
        "CONSTRUCTION_SITES": {
            "view_permission": "Construction.view_site",
            "add_permission": "Construction.add_site",
            "change_permission": "Construction.change_site",
            "delete_permission": "Construction.delete_site",
        },
        "CONSTRUCTION_TASKS": {
            "view_permission": "Construction.view_task",
            "add_permission": "Construction.add_task",
            "change_permission": "Construction.change_task",
            "delete_permission": "Construction.delete_task",
        },
        "INVENTORY_DASHBOARD": {"view_permission": "inventory.view_product"},
        "INVENTORY_PRODUCTS": {
            "view_permission": "inventory.view_product",
            "add_permission": "inventory.add_product",
            "change_permission": "inventory.change_product",
            "delete_permission": "inventory.delete_product",
        },
        "INVENTORY_RAW_MATERIALS": {
            "view_permission": "inventory.view_rawmaterial",
            "add_permission": "inventory.add_rawmaterial",
            "change_permission": "inventory.change_rawmaterial",
            "delete_permission": "inventory.delete_rawmaterial",
        },
        "INVENTORY_STOCK_MOVEMENTS": {
            "view_permission": "inventory.view_stockmovement",
            "add_permission": "inventory.add_stockmovement",
            "change_permission": "inventory.change_stockmovement",
            "delete_permission": "inventory.delete_stockmovement",
        },
        "ASSET_LIST": {"view_permission": "inventory.view_asset"},
        "ASSET_ASSIGNMENTS": {
            "view_permission": "inventory.view_assetassignment"
        },
        "AUDIT_LOGS": {"view_permission": "core.view_auditlog"},
    }

    for feature_code, permissions in permission_map.items():
        Feature.objects.filter(code=feature_code).update(**permissions)


def migrate_role_features_to_group_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    action_fields = (
        ("can_view", "view_permission"),
        ("can_add", "add_permission"),
        ("can_edit", "change_permission"),
        ("can_delete", "delete_permission"),
        ("can_approve", "approve_permission"),
    )

    role_features = RoleFeature.objects.select_related("role", "feature")
    for role_feature in role_features.iterator():
        permission_ids = []

        for legacy_field, feature_field in action_fields:
            if not getattr(role_feature, legacy_field):
                continue

            permission_name = getattr(
                role_feature.feature,
                feature_field,
                "",
            ).strip()
            if not permission_name or "." not in permission_name:
                continue

            app_label, codename = permission_name.split(".", 1)
            permission = Permission.objects.filter(
                content_type__app_label__iexact=app_label,
                codename=codename,
            ).first()
            if permission:
                permission_ids.append(permission.pk)

        if permission_ids:
            group = Group.objects.get(pk=role_feature.role_id)
            group.permissions.add(*permission_ids)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_approvalrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="feature",
            name="view_permission",
            field=models.CharField(
                blank=True,
                help_text="Django permission required to see and open this feature.",
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="feature",
            name="add_permission",
            field=models.CharField(
                blank=True,
                help_text="Django permission required to create records.",
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="feature",
            name="change_permission",
            field=models.CharField(
                blank=True,
                help_text="Django permission required to edit records.",
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="feature",
            name="delete_permission",
            field=models.CharField(
                blank=True,
                help_text="Django permission required to delete records.",
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="feature",
            name="approve_permission",
            field=models.CharField(
                blank=True,
                help_text="Custom Django permission required to approve records.",
                max_length=150,
            ),
        ),
        migrations.RunPython(
            configure_feature_permissions,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            migrate_role_features_to_group_permissions,
            migrations.RunPython.noop,
        ),
    ]
