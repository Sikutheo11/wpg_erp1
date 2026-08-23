from django.db import migrations


FEATURES = {
    "FURNITURE_DASHBOARD": ("Dashboard", "furniture:furniture_dashboard", 1, {"view_permission": "furniture.view_productionjob"}),
    "FURNITURE_PRODUCTION_JOBS": ("Production Jobs", "furniture:production_job_list", 2, {"view_permission": "furniture.view_productionjob", "add_permission": "furniture.add_productionjob", "change_permission": "furniture.change_productionjob", "delete_permission": "furniture.delete_productionjob"}),
    "FURNITURE_QUOTATIONS": ("Quotations", "furniture:quotation_list", 3, {"view_permission": "furniture.view_quotation", "add_permission": "furniture.add_quotation", "change_permission": "furniture.change_quotation", "delete_permission": "furniture.delete_quotation", "approve_permission": "furniture.approve_quotation"}),
    "FURNITURE_MATERIALS": ("Materials", "furniture:material_list", 4, {"view_permission": "furniture.view_productionmaterial", "add_permission": "furniture.add_productionmaterial", "change_permission": "furniture.change_productionmaterial", "delete_permission": "furniture.delete_productionmaterial"}),
    "FURNITURE_OUTPUTS": ("Outputs", "furniture:output_list", 5, {"view_permission": "furniture.view_productionoutput", "add_permission": "furniture.add_productionoutput", "change_permission": "furniture.change_productionoutput", "delete_permission": "furniture.delete_productionoutput"}),
    "FURNITURE_ORDERS": ("Legacy Orders", "furniture:order_list", 6, {"view_permission": "furniture.view_order", "add_permission": "furniture.add_order", "change_permission": "furniture.change_order", "delete_permission": "furniture.delete_order"}),
    "FURNITURE_TASKS": ("Production Tasks", "furniture:production_task_list", 7, {"view_permission": "furniture.view_productiontask", "add_permission": "furniture.add_productiontask", "change_permission": "furniture.change_productiontask", "delete_permission": "furniture.delete_productiontask"}),
    "FURNITURE_MY_TASKS": ("My Tasks", "furniture:my_production_tasks", 8, {"view_permission": "furniture.view_productiontask"}),
    "FURNITURE_LABOUR": ("Labour", "furniture:labour_list", 9, {"view_permission": "furniture.view_productionlabour", "add_permission": "furniture.add_productionlabour", "change_permission": "furniture.change_productionlabour", "delete_permission": "furniture.delete_productionlabour"}),
    "FURNITURE_MACHINES": ("Machines", "furniture:machine_list", 10, {"view_permission": "furniture.view_productionmachine", "add_permission": "furniture.add_productionmachine", "change_permission": "furniture.change_productionmachine", "delete_permission": "furniture.delete_productionmachine"}),
    "FURNITURE_QUALITY": ("Quality", "furniture:quality_inspection_list", 11, {"view_permission": "furniture.view_qualityinspection", "add_permission": "furniture.add_qualityinspection", "change_permission": "furniture.change_qualityinspection", "delete_permission": "furniture.delete_qualityinspection", "approve_permission": "furniture.approve_qualityinspection"}),
    "FURNITURE_REWORK": ("Rework", "furniture:rework_order_list", 12, {"view_permission": "furniture.view_reworkorder", "add_permission": "furniture.add_reworkorder", "change_permission": "furniture.change_reworkorder", "delete_permission": "furniture.delete_reworkorder", "approve_permission": "furniture.verify_reworkorder"}),
    "FURNITURE_REPORTS": ("Reports", "furniture:production_reports", 13, {"view_permission": "furniture.view_productionjob"}),
    "FURNITURE_SETTINGS": ("Settings", "furniture:production_settings", 14, {"view_permission": "furniture.view_productionsettings", "change_permission": "furniture.change_productionsettings"}),
}


INHERIT_FROM = {
    "FURNITURE_ORDERS": ("FURNITURE_PRODUCTION_JOBS",),
    "FURNITURE_TASKS": ("FURNITURE_PRODUCTION_JOBS",),
    "FURNITURE_MY_TASKS": ("FURNITURE_PRODUCTION_JOBS",),
    "FURNITURE_LABOUR": ("FURNITURE_MATERIALS",),
    "FURNITURE_MACHINES": ("FURNITURE_MATERIALS",),
    "FURNITURE_QUALITY": ("FURNITURE_PRODUCTION_JOBS",),
    "FURNITURE_REWORK": ("FURNITURE_PRODUCTION_JOBS",),
    "FURNITURE_REPORTS": ("FURNITURE_DASHBOARD",),
    "FURNITURE_SETTINGS": ("FURNITURE_PRODUCTION_JOBS",),
}


def find_permission(Permission, name):
    app_label, codename = name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()


def configure_furniture_permissions(apps, schema_editor):
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    business_unit, _ = BusinessUnit.objects.get_or_create(
        code="FURNITURE",
        defaults={"name": "Furniture & Manufacturing", "order": 1, "is_active": True},
    )
    custom_permissions = (
        ("quotation", "approve_quotation", "Can approve furniture quotations"),
        ("qualityinspection", "approve_qualityinspection", "Can approve furniture quality inspections"),
        ("reworkorder", "verify_reworkorder", "Can verify furniture rework orders"),
    )
    for model, codename, name in custom_permissions:
        content_type, _ = ContentType.objects.get_or_create(
            app_label="furniture",
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
                "icon": "bi bi-hammer",
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
        ("core", "0019_configure_agriculture_permissions"),
        ("furniture", "0020_alter_qualityinspection_quotation_and_more"),
    ]

    operations = [
        migrations.RunPython(configure_furniture_permissions, migrations.RunPython.noop),
    ]
