from django.db import migrations


FEATURES = {
    "CONSTRUCTION_DASHBOARD": ("Dashboard", "Construction:construction_dashboard", 1, {"view_permission": "Construction.view_project"}),
    "CONSTRUCTION_PROJECTS": ("Projects", "Construction:project_list", 2, {"view_permission": "Construction.view_project", "add_permission": "Construction.add_project", "change_permission": "Construction.change_project", "delete_permission": "Construction.delete_project"}),
    "CONSTRUCTION_SITES": ("Sites", "Construction:project_list", 3, {"view_permission": "Construction.view_site", "add_permission": "Construction.add_site", "change_permission": "Construction.change_site", "delete_permission": "Construction.delete_site"}),
    "CONSTRUCTION_TASKS": ("Tasks", "Construction:project_list", 4, {"view_permission": "Construction.view_task", "add_permission": "Construction.add_task", "change_permission": "Construction.change_task", "delete_permission": "Construction.delete_task"}),
    "CONSTRUCTION_MATERIALS": ("Materials", "Construction:project_list", 5, {"view_permission": "Construction.view_constructionmaterial", "add_permission": "Construction.add_constructionmaterial", "change_permission": "Construction.change_constructionmaterial", "delete_permission": "Construction.delete_constructionmaterial"}),
    "CONSTRUCTION_LABOUR": ("Labour", "Construction:project_list", 6, {"view_permission": "Construction.view_constructionlabour", "add_permission": "Construction.add_constructionlabour", "change_permission": "Construction.change_constructionlabour", "delete_permission": "Construction.delete_constructionlabour"}),
    "CONSTRUCTION_ASSET_USAGE": ("Asset Usage", "Construction:project_list", 7, {"view_permission": "Construction.view_constructionassetusage", "add_permission": "Construction.add_constructionassetusage", "change_permission": "Construction.change_constructionassetusage", "delete_permission": "Construction.delete_constructionassetusage"}),
    "CONSTRUCTION_EXPENSES": ("Expenses", "Construction:project_list", 8, {"view_permission": "Construction.view_constructionexpense", "add_permission": "Construction.add_constructionexpense", "change_permission": "Construction.change_constructionexpense", "delete_permission": "Construction.delete_constructionexpense"}),
}


INHERIT_FROM = {
    "CONSTRUCTION_MATERIALS": ("CONSTRUCTION_PROJECTS",),
    "CONSTRUCTION_LABOUR": ("CONSTRUCTION_PROJECTS",),
    "CONSTRUCTION_ASSET_USAGE": ("CONSTRUCTION_PROJECTS",),
    "CONSTRUCTION_EXPENSES": ("CONSTRUCTION_PROJECTS",),
}


def find_permission(Permission, name):
    app_label, codename = name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()


def configure_construction_permissions(apps, schema_editor):
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    business_unit, _ = BusinessUnit.objects.get_or_create(
        code="CONSTRUCTION",
        defaults={
            "name": "Construction & Built Environment",
            "description": "WPG Construction business unit.",
            "icon": "bi bi-building",
            "order": 2,
            "is_active": True,
        },
    )

    for code, (name, url_name, order, permissions) in FEATURES.items():
        Feature.objects.update_or_create(
            code=code,
            defaults={
                "business_unit": business_unit,
                "engine": None,
                "name": name,
                "url_name": url_name,
                "icon": "bi bi-building",
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

    # New detail features inherit only visibility from legacy project access.
    # Add/change/delete remain explicit to avoid widening financial or stock
    # authority for supervisors who could merely edit a project.
    for target_code, source_codes in INHERIT_FROM.items():
        target = Feature.objects.get(code=target_code)
        name = target.view_permission.strip()
        permission = find_permission(Permission, name) if name else None
        if not permission:
            continue
        group_ids = RoleFeature.objects.filter(
            feature__code__in=source_codes,
            can_view=True,
        ).values_list("role_id", flat=True).distinct()
        for group in Group.objects.filter(pk__in=group_ids):
            group.permissions.add(permission.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_configure_ecommerce_permissions"),
        ("Construction", "0006_alter_constructionmaterial_date"),
    ]

    operations = [
        migrations.RunPython(
            configure_construction_permissions,
            migrations.RunPython.noop,
        ),
    ]
