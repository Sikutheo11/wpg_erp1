from django.db import migrations


# Canonical configuration captured from the validated local environment.
# This migration reconciles configuration metadata only; it does not touch
# operational/business records.
FEATURES = {
    # Inventory Engine
    "INVENTORY_CATEGORIES": {
        "owner": ("engine", "INVENTORY"),
        "name": "Categories",
        "url_name": "inventory:category_list",
        "order": 2,
    },
    "INVENTORY_WAREHOUSES": {
        "owner": ("engine", "INVENTORY"),
        "name": "Warehouses",
        "url_name": "inventory:warehouse_list",
        "order": 3,
    },
    "INVENTORY_SUPPLIERS": {
        "owner": ("engine", "INVENTORY"),
        "name": "Suppliers",
        "url_name": "inventory:supplier_list",
        "order": 4,
    },
    "INVENTORY_LOW_STOCK": {
        "owner": ("engine", "INVENTORY"),
        "name": "Low Stock",
        "url_name": "inventory:low_stock",
        "order": 8,
    },

    # Agriculture Business Unit
    "AGRICULTURE_DASHBOARD": {"owner": ("business_unit", "AGRICULTURE"), "name": "Dashboard", "url_name": "agriculture:dashboard", "order": 1},
    "AGRICULTURE_FARMS": {"owner": ("business_unit", "AGRICULTURE"), "name": "Farms", "url_name": "agriculture:farm_list", "order": 2},
    "AGRICULTURE_HOUSES": {"owner": ("business_unit", "AGRICULTURE"), "name": "Poultry Houses", "url_name": "agriculture:farm_list", "order": 3},
    "AGRICULTURE_BREEDS": {"owner": ("business_unit", "AGRICULTURE"), "name": "Breeds", "url_name": "agriculture:breed_list", "order": 4},
    "AGRICULTURE_FLOCKS": {"owner": ("business_unit", "AGRICULTURE"), "name": "Flocks", "url_name": "agriculture:flock_list", "order": 5},
    "AGRICULTURE_OPERATIONS": {"owner": ("business_unit", "AGRICULTURE"), "name": "Operations", "url_name": "agriculture:operation_list", "order": 6},
    "AGRICULTURE_DAILY_RECORDS": {"owner": ("business_unit", "AGRICULTURE"), "name": "Daily Records", "url_name": "agriculture:flock_list", "order": 7},
    "AGRICULTURE_EGG_PRODUCTION": {"owner": ("business_unit", "AGRICULTURE"), "name": "Egg Production", "url_name": "agriculture:flock_list", "order": 8},
    "AGRICULTURE_FEEDING": {"owner": ("business_unit", "AGRICULTURE"), "name": "Feeding", "url_name": "agriculture:flock_list", "order": 9},
    "AGRICULTURE_HEALTH": {"owner": ("business_unit", "AGRICULTURE"), "name": "Health", "url_name": "agriculture:flock_list", "order": 10},
    "AGRICULTURE_MORTALITY": {"owner": ("business_unit", "AGRICULTURE"), "name": "Mortality", "url_name": "agriculture:flock_list", "order": 11},
    "AGRICULTURE_INCUBATION": {"owner": ("business_unit", "AGRICULTURE"), "name": "Incubation", "url_name": "agriculture:incubation_list", "order": 12},
    "AGRICULTURE_REPORTS": {"owner": ("business_unit", "AGRICULTURE"), "name": "Valuation Report", "url_name": "agriculture:valuation_report", "order": 13},

    # Shared enterprise engines
    "ORDER_LIST": {"owner": ("engine", "ORDER"), "name": "Order Types", "url_name": "orders:order_list", "order": 1},
    "ORDER_RESTOCK": {"owner": ("engine", "ORDER"), "name": "New Order", "url_name": "orders:business_unit_select", "order": 2},
    "ORDER_APPROVAL": {"owner": ("engine", "ORDER"), "name": "All Orders", "url_name": "orders:all_order_business_units", "order": 3},
    "ORDER_FULFILMENT": {"owner": ("engine", "ORDER"), "name": "Order Fulfilment", "url_name": "orders:all_orders", "order": 4},
    "QUOTATION_LIST": {"owner": ("engine", "QUOTATION"), "name": "Customer Quotations", "url_name": "sales:quotation_list", "order": 1},
    "QUOTATION_APPROVAL": {"owner": ("engine", "QUOTATION"), "name": "Customer Quotation Approval", "url_name": "sales:quotation_list", "order": 2},
    "ASSET_LIST": {"owner": ("engine", "ASSET"), "name": "Assets", "url_name": "inventory:asset_list", "order": 1},
    "ASSET_ASSIGNMENTS": {"owner": ("engine", "ASSET"), "name": "Asset Assignments", "url_name": "inventory:asset_assignment_list", "order": 2},
    "APPROVAL_PENDING": {"owner": ("engine", "APPROVAL"), "name": "Pending Approvals", "url_name": "core:approval_request_list", "order": 1},
    "APPROVAL_HISTORY": {"owner": ("engine", "APPROVAL"), "name": "Approval History", "url_name": "core:approval_request_list", "order": 2},
    "NOTIFICATION_LIST": {"owner": ("engine", "NOTIFICATION"), "name": "Notifications", "url_name": "core:notification_list", "order": 1},
    "REPORTING_REPORTS": {"owner": ("engine", "REPORTING"), "name": "Reports", "url_name": "core:reports_home", "order": 2},
}


def reconcile_configuration(apps, schema_editor):
    Feature = apps.get_model("core", "Feature")
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    EnterpriseEngine = apps.get_model("core", "EnterpriseEngine")
    RoleFeature = apps.get_model("core", "RoleFeature")

    for code, spec in FEATURES.items():
        owner_type, owner_code = spec["owner"]

        owner_defaults = {"business_unit": None, "engine": None}
        if owner_type == "business_unit":
            owner = BusinessUnit.objects.filter(code=owner_code).first()
            if owner is None:
                continue
            owner_defaults["business_unit"] = owner
        else:
            owner = EnterpriseEngine.objects.filter(code=owner_code).first()
            if owner is None:
                continue
            owner_defaults["engine"] = owner

        feature, created = Feature.objects.update_or_create(
            code=code,
            defaults={
                **owner_defaults,
                "name": spec["name"],
                "url_name": spec["url_name"],
                "order": spec["order"],
                "is_active": True,
            },
        )

        # If a feature was absent in production but CEO already has a canonical
        # all-features role policy, make the new feature visible there too.
        # Existing role assignments for existing features are never overwritten.
        if created:
            ceo_role_features = RoleFeature.objects.filter(
                role__name="CEO"
            )
            if ceo_role_features.exists():
                RoleFeature.objects.get_or_create(
                    role_id=ceo_role_features.values_list("role_id", flat=True).first(),
                    feature=feature,
                    defaults={
                        "can_view": True,
                        "can_add": True,
                        "can_edit": True,
                        "can_delete": True,
                        "can_approve": True,
                    },
                )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0029_sync_furniture_navigation"),
    ]

    operations = [
        migrations.RunPython(reconcile_configuration, migrations.RunPython.noop),
    ]
