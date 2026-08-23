from django.db import migrations


PERMISSIONS = {
    "AGRICULTURE_DASHBOARD": {"view_permission": "agriculture.view_agricultureoperation"},
    "AGRICULTURE_FARMS": {"view_permission": "agriculture.view_poultryfarm", "add_permission": "agriculture.add_poultryfarm", "change_permission": "agriculture.change_poultryfarm", "delete_permission": "agriculture.delete_poultryfarm"},
    "AGRICULTURE_HOUSES": {"view_permission": "agriculture.view_poultryhouse", "add_permission": "agriculture.add_poultryhouse", "change_permission": "agriculture.change_poultryhouse", "delete_permission": "agriculture.delete_poultryhouse"},
    "AGRICULTURE_BREEDS": {"view_permission": "agriculture.view_poultrybreed", "add_permission": "agriculture.add_poultrybreed", "change_permission": "agriculture.change_poultrybreed", "delete_permission": "agriculture.delete_poultrybreed"},
    "AGRICULTURE_OPERATIONS": {"view_permission": "agriculture.view_agricultureoperation", "add_permission": "agriculture.add_agricultureoperation", "change_permission": "agriculture.change_agricultureoperation", "delete_permission": "agriculture.delete_agricultureoperation"},
    "AGRICULTURE_FLOCKS": {"view_permission": "agriculture.view_poultryflock", "add_permission": "agriculture.add_poultryflock", "change_permission": "agriculture.change_poultryflock", "delete_permission": "agriculture.delete_poultryflock"},
    "AGRICULTURE_DAILY_RECORDS": {"view_permission": "agriculture.view_dailyflockrecord", "add_permission": "agriculture.add_dailyflockrecord", "change_permission": "agriculture.change_dailyflockrecord", "delete_permission": "agriculture.delete_dailyflockrecord"},
    "AGRICULTURE_EGG_PRODUCTION": {"view_permission": "agriculture.view_eggproduction", "add_permission": "agriculture.add_eggproduction", "change_permission": "agriculture.change_eggproduction", "delete_permission": "agriculture.delete_eggproduction"},
    "AGRICULTURE_FEEDING": {"view_permission": "agriculture.view_feedingrecord", "add_permission": "agriculture.add_feedingrecord", "change_permission": "agriculture.change_feedingrecord", "delete_permission": "agriculture.delete_feedingrecord", "approve_permission": "agriculture.change_feedingrecord"},
    "AGRICULTURE_HEALTH": {"view_permission": "agriculture.view_healthrecord", "add_permission": "agriculture.add_healthrecord", "change_permission": "agriculture.change_healthrecord", "delete_permission": "agriculture.delete_healthrecord", "approve_permission": "agriculture.change_healthrecord"},
    "AGRICULTURE_MORTALITY": {"view_permission": "agriculture.view_mortalityrecord", "add_permission": "agriculture.add_mortalityrecord", "change_permission": "agriculture.change_mortalityrecord", "delete_permission": "agriculture.delete_mortalityrecord"},
    "AGRICULTURE_INCUBATION": {"view_permission": "agriculture.view_incubationbatch", "add_permission": "agriculture.add_incubationbatch", "change_permission": "agriculture.change_incubationbatch", "delete_permission": "agriculture.delete_incubationbatch"},
    "AGRICULTURE_REPORTS": {"view_permission": "agriculture.view_agricultureoperation"},
    "AGRICULTURE_OPERATION_SUBMIT": {"change_permission": "agriculture.change_agricultureoperation"},
    "AGRICULTURE_OPERATION_APPROVE": {"approve_permission": "agriculture.approve_agricultureoperation"},
    "AGRICULTURE_OPERATION_START": {"change_permission": "agriculture.change_agricultureoperation"},
    "AGRICULTURE_OPERATION_HOLD": {"change_permission": "agriculture.change_agricultureoperation"},
    "AGRICULTURE_OPERATION_RESUME": {"change_permission": "agriculture.change_agricultureoperation"},
    "AGRICULTURE_OPERATION_COMPLETE": {"approve_permission": "agriculture.complete_agricultureoperation"},
    "AGRICULTURE_OPERATION_CANCEL": {"delete_permission": "agriculture.delete_agricultureoperation"},
}


FEATURE_META = {
    "AGRICULTURE_DASHBOARD": ("Agriculture Dashboard", "agriculture:dashboard", 10),
    "AGRICULTURE_FARMS": ("Poultry Farms", "agriculture:farm_list", 20),
    "AGRICULTURE_HOUSES": ("Poultry Houses", "agriculture:farm_list", 30),
    "AGRICULTURE_BREEDS": ("Poultry Breeds", "agriculture:breed_list", 40),
    "AGRICULTURE_OPERATIONS": ("Agriculture Operations", "agriculture:operation_list", 50),
    "AGRICULTURE_FLOCKS": ("Poultry Flocks", "agriculture:flock_list", 60),
    "AGRICULTURE_DAILY_RECORDS": ("Daily Flock Records", "agriculture:flock_list", 70),
    "AGRICULTURE_EGG_PRODUCTION": ("Egg Production", "agriculture:flock_list", 80),
    "AGRICULTURE_FEEDING": ("Feeding Records", "agriculture:flock_list", 90),
    "AGRICULTURE_HEALTH": ("Health and Vaccination", "agriculture:flock_list", 100),
    "AGRICULTURE_MORTALITY": ("Mortality Records", "agriculture:flock_list", 110),
    "AGRICULTURE_INCUBATION": ("Incubation and Hatching", "agriculture:incubation_list", 120),
    "AGRICULTURE_REPORTS": ("Agriculture Reports", "agriculture:valuation_report", 130),
    "AGRICULTURE_OPERATION_SUBMIT": ("Submit Agriculture Operation", "", 201),
    "AGRICULTURE_OPERATION_APPROVE": ("Approve Agriculture Operation", "", 202),
    "AGRICULTURE_OPERATION_START": ("Start Agriculture Operation", "", 203),
    "AGRICULTURE_OPERATION_HOLD": ("Hold Agriculture Operation", "", 204),
    "AGRICULTURE_OPERATION_RESUME": ("Resume Agriculture Operation", "", 205),
    "AGRICULTURE_OPERATION_COMPLETE": ("Complete Agriculture Operation", "", 206),
    "AGRICULTURE_OPERATION_CANCEL": ("Cancel Agriculture Operation", "", 207),
}


def find_permission(Permission, permission_name):
    app_label, codename = permission_name.split(".", 1)
    return Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).first()


def configure_agriculture_permissions(apps, schema_editor):
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Feature = apps.get_model("core", "Feature")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    RoleFeature = apps.get_model("core", "RoleFeature")

    business_unit, _ = BusinessUnit.objects.get_or_create(
        code="AGRICULTURE",
        defaults={
            "name": "Agriculture",
            "description": "WPG Agriculture and Poultry business unit.",
            "icon": "fas fa-seedling",
            "order": 3,
            "is_active": True,
        },
    )

    content_type, _ = ContentType.objects.get_or_create(
        app_label="agriculture",
        model="agricultureoperation",
    )
    for codename, name in (
        ("approve_agricultureoperation", "Can approve or return agriculture operations"),
        ("complete_agricultureoperation", "Can complete agriculture operations"),
    ):
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )

    for code, values in PERMISSIONS.items():
        name, url_name, order = FEATURE_META[code]
        Feature.objects.update_or_create(
            code=code,
            defaults={
                "business_unit": business_unit,
                "engine": None,
                "name": name,
                "url_name": url_name,
                "icon": "fas fa-seedling",
                "order": order,
                "is_active": True,
                **values,
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
        feature__code__in=tuple(PERMISSIONS),
    ).select_related("role", "feature")
    for role_feature in role_features.iterator():
        permission_ids = []
        for legacy_field, feature_field in action_fields:
            if not getattr(role_feature, legacy_field):
                continue
            permission_name = getattr(role_feature.feature, feature_field, "").strip()
            permission = (
                find_permission(Permission, permission_name)
                if permission_name
                else None
            )
            if permission:
                permission_ids.append(permission.pk)
        if permission_ids:
            Group.objects.get(pk=role_feature.role_id).permissions.add(*permission_ids)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_configure_sales_order_permissions"),
        ("agriculture", "0002_alter_agricultureoperation_options"),
    ]

    operations = [
        migrations.RunPython(
            configure_agriculture_permissions,
            migrations.RunPython.noop,
        ),
    ]
