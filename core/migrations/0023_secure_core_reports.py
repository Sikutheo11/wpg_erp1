from django.db import migrations


REPORT_FEATURES = {
    "CONSTRUCTION_REPORTS": {
        "name": "Construction Reports",
        "url_name": "core:construction_report",
        "permission": "Construction.view_project",
        "owner": "business_unit",
        "owner_code": "CONSTRUCTION",
        "order": 9,
    },
    "INVENTORY_REPORTS": {
        "name": "Inventory Reports",
        "url_name": "core:inventory_report",
        "permission": "inventory.view_product",
        "owner": "engine",
        "owner_code": "INVENTORY",
        "order": 5,
    },
    "REPORTING_EXECUTIVE_DASHBOARD": {
        "name": "Executive Dashboard",
        "url_name": "core:executive_report",
        "permission": "core.view_executivereport",
        "owner": "engine",
        "owner_code": "REPORTING",
        "order": 1,
    },
    "REPORTING_REPORTS": {
        "name": "Reports Centre",
        "url_name": "core:reports_home",
        "permission": "core.view_reports",
        "owner": "engine",
        "owner_code": "REPORTING",
        "order": 2,
    },
}


def find_permission(Permission, name):
    app_label, codename = name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()


def configure_report_permissions(apps, schema_editor):
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    ContentType = apps.get_model("contenttypes", "ContentType")
    EnterpriseEngine = apps.get_model("core", "EnterpriseEngine")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="core",
        model="auditlog",
    )
    for codename, name in (
        ("view_reports", "Can access the reports centre"),
        ("view_executivereport", "Can view executive reports"),
    ):
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )

    for code, config in REPORT_FEATURES.items():
        owner_defaults = {
            "business_unit": None,
            "engine": None,
        }
        if config["owner"] == "business_unit":
            owner_defaults["business_unit"] = BusinessUnit.objects.get(
                code=config["owner_code"],
            )
        else:
            engine, _ = EnterpriseEngine.objects.get_or_create(
                code=config["owner_code"],
                defaults={
                    "name": config["owner_code"].title(),
                    "order": 99,
                    "is_active": True,
                },
            )
            owner_defaults["engine"] = engine

        feature, _ = Feature.objects.update_or_create(
            code=code,
            defaults={
                **owner_defaults,
                "name": config["name"],
                "url_name": config["url_name"],
                "icon": "bi bi-bar-chart",
                "order": config["order"],
                "is_active": True,
                "view_permission": config["permission"],
                "add_permission": "",
                "change_permission": "",
                "delete_permission": "",
                "approve_permission": "",
            },
        )

        permission = find_permission(Permission, config["permission"])
        if not permission:
            continue
        group_ids = RoleFeature.objects.filter(
            feature=feature,
            can_view=True,
        ).values_list("role_id", flat=True)
        for group in Group.objects.filter(pk__in=group_ids):
            group.permissions.add(permission.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_configure_construction_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="auditlog",
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    ("view_reports", "Can access the reports centre"),
                    ("view_executivereport", "Can view executive reports"),
                ],
            },
        ),
        migrations.RunPython(
            configure_report_permissions,
            migrations.RunPython.noop,
        ),
    ]
