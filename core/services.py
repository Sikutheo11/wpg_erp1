from django.contrib.auth.models import Group

from .models import (
    BusinessUnit,
    EnterpriseEngine,
    Module,
    Feature,
    RoleFeature,
    DashboardCard,
    KPIWidget,
)

from .initial_data import (
    BUSINESS_UNITS,
    ENTERPRISE_ENGINES,
    MODULES,
    BUSINESS_UNIT_FEATURES,
    ENGINE_FEATURES,
    DASHBOARD_CARDS,
    KPI_WIDGETS,
    GROUPS,
    ROLE_FEATURES,
)


class CoreSetupService:
    """
    WPG BOS Core synchronization service.
    """

    @staticmethod
    def sync_business_units():
        created_count = 0
        updated_count = 0

        for item in BUSINESS_UNITS:
            obj, created = BusinessUnit.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "icon": item.get("icon", ""),
                    "order": item.get("order", 0),
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_enterprise_engines():
        created_count = 0
        updated_count = 0

        for item in ENTERPRISE_ENGINES:
            obj, created = EnterpriseEngine.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "icon": item.get("icon", ""),
                    "order": item.get("order", 0),
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_modules():
        """
        Legacy modules.
        Keep temporarily until old Module/RoleModule/DashboardCard dependency is fully removed.
        """
        created_count = 0
        updated_count = 0

        for item in MODULES:
            obj, created = Module.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "icon": item.get("icon", ""),
                    "url_name": item.get("url_name", ""),
                    "permission": item.get("permission", ""),
                    "order": item.get("order", 0),
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_business_unit_features():
        created_count = 0
        updated_count = 0

        for business_unit_code, features in BUSINESS_UNIT_FEATURES.items():
            try:
                business_unit = BusinessUnit.objects.get(
                    code=business_unit_code
                )
            except BusinessUnit.DoesNotExist:
                continue

            for name, code, url_name, icon, order in features:
                obj, created = Feature.objects.update_or_create(
                    code=code,
                    defaults={
                        "business_unit": business_unit,
                        "engine": None,
                        "name": name,
                        "url_name": url_name,
                        "icon": icon,
                        "order": order,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_engine_features():
        created_count = 0
        updated_count = 0

        for engine_code, features in ENGINE_FEATURES.items():
            try:
                engine = EnterpriseEngine.objects.get(
                    code=engine_code
                )
            except EnterpriseEngine.DoesNotExist:
                continue

            for name, code, url_name, icon, order in features:
                obj, created = Feature.objects.update_or_create(
                    code=code,
                    defaults={
                        "business_unit": None,
                        "engine": engine,
                        "name": name,
                        "url_name": url_name,
                        "icon": icon,
                        "order": order,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_groups():
        created_count = 0
        updated_count = 0

        for group_name in GROUPS:
            group, created = Group.objects.get_or_create(
                name=group_name
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count

    @staticmethod
    def _apply_permissions(role_feature, permissions):
        role_feature.can_view = permissions.get("view", False)
        role_feature.can_add = permissions.get("add", False)
        role_feature.can_edit = permissions.get("edit", False)
        role_feature.can_delete = permissions.get("delete", False)
        role_feature.can_approve = permissions.get("approve", False)
        role_feature.save()

    @staticmethod
    def sync_role_features():
        created_count = 0
        updated_count = 0

        for group_name, features in ROLE_FEATURES.items():
            try:
                group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                continue

            if "ALL" in features:
                permissions = features["ALL"]

                for feature in Feature.objects.filter(is_active=True):
                    role_feature, created = RoleFeature.objects.get_or_create(
                        role=group,
                        feature=feature,
                    )

                    CoreSetupService._apply_permissions(
                        role_feature,
                        permissions,
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                continue

            for feature_code, permissions in features.items():
                try:
                    feature = Feature.objects.get(code=feature_code)
                except Feature.DoesNotExist:
                    continue

                role_feature, created = RoleFeature.objects.get_or_create(
                    role=group,
                    feature=feature,
                )

                CoreSetupService._apply_permissions(
                    role_feature,
                    permissions,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_dashboard_cards():
        created_count = 0
        updated_count = 0

        for module_code, cards in DASHBOARD_CARDS.items():
            try:
                module = Module.objects.get(code=module_code)
            except Module.DoesNotExist:
                continue

            for title, code, icon, color, order in cards:
                obj, created = DashboardCard.objects.update_or_create(
                    code=code,
                    defaults={
                        "module": module,
                        "title": title,
                        "icon": icon,
                        "color": color,
                        "order": order,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count

    @staticmethod
    def sync_kpi_widgets():
        created_count = 0
        updated_count = 0

        # Business Unit KPI Widgets
        for business_unit_code, widgets in KPI_WIDGETS.get("business_units", {}).items():
            try:
                business_unit = BusinessUnit.objects.get(code=business_unit_code)
            except BusinessUnit.DoesNotExist:
                continue

            for title, code, widget_type, data_source, value_key, icon, color, order in widgets:
                obj, created = KPIWidget.objects.update_or_create(
                    code=code,
                    defaults={
                        "business_unit": business_unit,
                        "engine": None,
                        "title": title,
                        "widget_type": widget_type,
                        "data_source": data_source,
                        "value_key": value_key,
                        "icon": icon,
                        "color": color,
                        "order": order,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        # Engine KPI Widgets
        for engine_code, widgets in KPI_WIDGETS.get("engines", {}).items():
            try:
                engine = EnterpriseEngine.objects.get(code=engine_code)
            except EnterpriseEngine.DoesNotExist:
                continue

            for title, code, widget_type, data_source, value_key, icon, color, order in widgets:
                obj, created = KPIWidget.objects.update_or_create(
                    code=code,
                    defaults={
                        "business_unit": None,
                        "engine": engine,
                        "title": title,
                        "widget_type": widget_type,
                        "data_source": data_source,
                        "value_key": value_key,
                        "icon": icon,
                        "color": color,
                        "order": order,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count
    
    @staticmethod
    def sync_all():
        business_units = CoreSetupService.sync_business_units()
        engines = CoreSetupService.sync_enterprise_engines()
        modules = CoreSetupService.sync_modules()
        business_unit_features = CoreSetupService.sync_business_unit_features()
        engine_features = CoreSetupService.sync_engine_features()
        groups = CoreSetupService.sync_groups()
        role_features = CoreSetupService.sync_role_features()
        cards = CoreSetupService.sync_dashboard_cards()
        kpi_widgets = CoreSetupService.sync_kpi_widgets()

        return {
            "business_units": {
                "created": business_units[0],
                "updated": business_units[1],
            },
            "enterprise_engines": {
                "created": engines[0],
                "updated": engines[1],
            },
            "modules": {
                "created": modules[0],
                "updated": modules[1],
            },
            "business_unit_features": {
                "created": business_unit_features[0],
                "updated": business_unit_features[1],
            },
            "engine_features": {
                "created": engine_features[0],
                "updated": engine_features[1],
            },
            "groups": {
                "created": groups[0],
                "updated": groups[1],
            },
            "role_features": {
                "created": role_features[0],
                "updated": role_features[1],
            },
            "dashboard_cards": {
                "created": cards[0],
                "updated": cards[1],
            },
            "kpi_widgets": {
                "created": kpi_widgets[0],
                "updated": kpi_widgets[1],
            },
        }