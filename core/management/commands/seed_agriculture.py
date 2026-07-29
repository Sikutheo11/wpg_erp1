from django.apps import apps
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    BusinessUnit,
    Feature,
    Module,
    RoleFeature,
    RoleModule,
)


class Command(BaseCommand):
    help = (
        "Seed the Agriculture/Poultry business unit, module, features, "
        "role permissions and dashboard KPIs without creating duplicates."
    )

    BUSINESS_UNIT = {
        "code": "AGRICULTURE",
        "name": "Agriculture",
        "description": (
            "WPG Agriculture business unit covering poultry farms, flocks, "
            "egg production, feeding, health, incubation and fulfilment."
        ),
    }

    MODULE = {
        "code": "AGRICULTURE",
        "name": "Agriculture",
        "icon": "fas fa-seedling",
        "url_name": "agriculture:dashboard",
        "permission": "agriculture.view_agricultureoperation",
        "order": 80,
        "is_active": True,
    }

    FEATURES = [
        {
            "code": "AGRICULTURE_DASHBOARD",
            "name": "Agriculture Dashboard",
            "url_name": "agriculture:dashboard",
            "icon": "fas fa-chart-line",
            "order": 10,
        },
        {
            "code": "AGRICULTURE_FARMS",
            "name": "Poultry Farms",
            "url_name": "agriculture:farm_list",
            "icon": "fas fa-tractor",
            "order": 20,
        },
        {
            "code": "AGRICULTURE_HOUSES",
            "name": "Poultry Houses",
            "url_name": "agriculture:house_create",
            "icon": "fas fa-warehouse",
            "order": 30,
        },
        {
            "code": "AGRICULTURE_BREEDS",
            "name": "Poultry Breeds",
            "url_name": "agriculture:breed_list",
            "icon": "fas fa-dna",
            "order": 40,
        },
        {
            "code": "AGRICULTURE_OPERATIONS",
            "name": "Agriculture Operations",
            "url_name": "agriculture:operation_list",
            "icon": "fas fa-list-check",
            "order": 50,
        },
        {
            "code": "AGRICULTURE_FLOCKS",
            "name": "Poultry Flocks",
            "url_name": "agriculture:flock_list",
            "icon": "fas fa-feather",
            "order": 60,
        },
        {
            "code": "AGRICULTURE_DAILY_RECORDS",
            "name": "Daily Flock Records",
            "url_name": "agriculture:flock_list",
            "icon": "fas fa-calendar-day",
            "order": 70,
        },
        {
            "code": "AGRICULTURE_EGG_PRODUCTION",
            "name": "Egg Production",
            "url_name": "agriculture:flock_list",
            "icon": "fas fa-egg",
            "order": 80,
        },
        {
            "code": "AGRICULTURE_FEEDING",
            "name": "Feeding Records",
            "url_name": "agriculture:flock_list",
            "icon": "fas fa-wheat-awn",
            "order": 90,
        },
        {
            "code": "AGRICULTURE_HEALTH",
            "name": "Health and Vaccination",
            "url_name": "agriculture:flock_list",
            "icon": "fas fa-syringe",
            "order": 100,
        },
        {
            "code": "AGRICULTURE_MORTALITY",
            "name": "Mortality Records",
            "url_name": "agriculture:flock_list",
            "icon": "fas fa-triangle-exclamation",
            "order": 110,
        },
        {
            "code": "AGRICULTURE_INCUBATION",
            "name": "Incubation and Hatching",
            "url_name": "agriculture:incubation_list",
            "icon": "fas fa-temperature-half",
            "order": 120,
        },
        {
            "code": "AGRICULTURE_REPORTS",
            "name": "Agriculture Reports",
            "url_name": "agriculture:valuation_report",
            "icon": "fas fa-chart-column",
            "order": 130,
        },
        # Core Workflow transition permissions.
        {
            "code": "AGRICULTURE_OPERATION_SUBMIT",
            "name": "Submit Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-paper-plane",
            "order": 201,
        },
        {
            "code": "AGRICULTURE_OPERATION_APPROVE",
            "name": "Approve Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-circle-check",
            "order": 202,
        },
        {
            "code": "AGRICULTURE_OPERATION_START",
            "name": "Start Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-play",
            "order": 203,
        },
        {
            "code": "AGRICULTURE_OPERATION_HOLD",
            "name": "Hold Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-pause",
            "order": 204,
        },
        {
            "code": "AGRICULTURE_OPERATION_RESUME",
            "name": "Resume Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-forward",
            "order": 205,
        },
        {
            "code": "AGRICULTURE_OPERATION_COMPLETE",
            "name": "Complete Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-check-double",
            "order": 206,
        },
        {
            "code": "AGRICULTURE_OPERATION_CANCEL",
            "name": "Cancel Agriculture Operation",
            "url_name": "",
            "icon": "fas fa-ban",
            "order": 207,
        },
    ]

    KPI_WIDGETS = [
        {
            "code": "AGRICULTURE_ACTIVE_FARMS",
            "title": "Active Farms",
            "widget_type": "number",
            "icon": "fas fa-tractor",
            "color": "success",
            "order": 10,
        },
        {
            "code": "AGRICULTURE_ACTIVE_FLOCKS",
            "title": "Active Flocks",
            "widget_type": "number",
            "icon": "fas fa-layer-group",
            "color": "primary",
            "order": 20,
        },
        {
            "code": "AGRICULTURE_CURRENT_BIRDS",
            "title": "Current Birds",
            "widget_type": "number",
            "icon": "fas fa-feather",
            "color": "warning",
            "order": 30,
        },
        {
            "code": "AGRICULTURE_EGG_PRODUCTION_CARD",
            "title": "Egg Production",
            "widget_type": "number",
            "icon": "fas fa-egg",
            "color": "success",
            "order": 40,
        },
        {
            "code": "AGRICULTURE_MORTALITY_CARD",
            "title": "Mortality Alerts",
            "widget_type": "alert",
            "icon": "fas fa-triangle-exclamation",
            "color": "danger",
            "order": 50,
        },
    ]

    ROLE_RULES = {
        "Admin": {
            "module": True,
            "features": "ALL",
            "can_view": True,
            "can_add": True,
            "can_edit": True,
            "can_delete": True,
            "can_approve": True,
        },
        "Manager": {
            "module": True,
            "features": "ALL",
            "can_view": True,
            "can_add": True,
            "can_edit": True,
            "can_delete": False,
            "can_approve": True,
        },
        "Agriculture Manager": {
            "module": True,
            "features": "ALL",
            "can_view": True,
            "can_add": True,
            "can_edit": True,
            "can_delete": False,
            "can_approve": True,
        },
        "Agriculture Officer": {
            "module": True,
            "features": {
                "AGRICULTURE_DASHBOARD",
                "AGRICULTURE_FARMS",
                "AGRICULTURE_HOUSES",
                "AGRICULTURE_BREEDS",
                "AGRICULTURE_OPERATIONS",
                "AGRICULTURE_FLOCKS",
                "AGRICULTURE_DAILY_RECORDS",
                "AGRICULTURE_EGG_PRODUCTION",
                "AGRICULTURE_FEEDING",
                "AGRICULTURE_HEALTH",
                "AGRICULTURE_MORTALITY",
                "AGRICULTURE_INCUBATION",
                "AGRICULTURE_OPERATION_SUBMIT",
                "AGRICULTURE_OPERATION_START",
                "AGRICULTURE_OPERATION_HOLD",
                "AGRICULTURE_OPERATION_RESUME",
                "AGRICULTURE_OPERATION_COMPLETE",
            },
            "can_view": True,
            "can_add": True,
            "can_edit": True,
            "can_delete": False,
            "can_approve": False,
        },
        "Poultry Worker": {
            "module": True,
            "features": {
                "AGRICULTURE_DASHBOARD",
                "AGRICULTURE_FLOCKS",
                "AGRICULTURE_DAILY_RECORDS",
                "AGRICULTURE_EGG_PRODUCTION",
                "AGRICULTURE_FEEDING",
                "AGRICULTURE_HEALTH",
                "AGRICULTURE_MORTALITY",
                "AGRICULTURE_INCUBATION",
            },
            "can_view": True,
            "can_add": True,
            "can_edit": True,
            "can_delete": False,
            "can_approve": False,
        },
    }

    @staticmethod
    def _field_names(model):
        return {
            field.name
            for field in model._meta.get_fields()
            if getattr(field, "concrete", False)
        }

    @classmethod
    def _supported(cls, model, values):
        fields = cls._field_names(model)
        return {
            key: value
            for key, value in values.items()
            if key in fields
        }

    @classmethod
    def _permission_defaults(cls, rule):
        values = {
            "can_view": rule["can_view"],
            "can_add": rule["can_add"],
            "can_edit": rule["can_edit"],
            "can_delete": rule["can_delete"],
            "can_approve": rule["can_approve"],
        }
        return cls._supported(RoleFeature, values)

    @classmethod
    def _seed_kpi_widgets(cls, business_unit, module):
        try:
            widget_model = apps.get_model("core", "KPIWidget")
        except LookupError:
            return 0

        count = 0
        for definition in cls.KPI_WIDGETS:
            defaults = {
                **definition,
                "module": module,
                "business_unit": business_unit,
                "engine": None,
                "is_active": True,
            }
            code = defaults.pop("code")
            widget_model.objects.update_or_create(
                code=code,
                defaults=cls._supported(widget_model, defaults),
            )
            count += 1
        return count

    @transaction.atomic
    def handle(self, *args, **options):
        business_unit, business_unit_created = (
            BusinessUnit.objects.update_or_create(
                code=self.BUSINESS_UNIT["code"],
                defaults=self._supported(
                    BusinessUnit,
                    {
                        "name": self.BUSINESS_UNIT["name"],
                        "description": self.BUSINESS_UNIT["description"],
                        "is_active": True,
                    },
                ),
            )
        )

        module_defaults = {
            **self.MODULE,
            "business_unit": business_unit,
            "engine": None,
        }
        module_code = module_defaults.pop("code")
        module, module_created = Module.objects.update_or_create(
            code=module_code,
            defaults=self._supported(Module, module_defaults),
        )

        features = {}
        feature_created_count = 0
        for definition in self.FEATURES:
            defaults = {
                **definition,
                "module": module,
                "business_unit": business_unit,
                "engine": None,
                "is_active": True,
            }
            code = defaults.pop("code")
            feature, created = Feature.objects.update_or_create(
                code=code,
                defaults=self._supported(Feature, defaults),
            )
            features[code] = feature
            feature_created_count += int(created)

        role_feature_count = 0
        for role_name, rule in self.ROLE_RULES.items():
            role, _ = Group.objects.get_or_create(name=role_name)

            RoleModule.objects.update_or_create(
                role=role,
                module=module,
                defaults=self._supported(
                    RoleModule,
                    {"can_view": rule["module"]},
                ),
            )

            allowed_codes = (
                set(features)
                if rule["features"] == "ALL"
                else set(rule["features"])
            )

            for code, feature in features.items():
                if code not in allowed_codes:
                    continue

                RoleFeature.objects.update_or_create(
                    role=role,
                    feature=feature,
                    defaults=self._permission_defaults(rule),
                )
                role_feature_count += 1

        widget_count = self._seed_kpi_widgets(
            business_unit=business_unit,
            module=module,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Agriculture seed completed successfully."
            )
        )
        self.stdout.write(
            f"Business unit: {business_unit.code} "
            f"({'created' if business_unit_created else 'updated'})"
        )
        self.stdout.write(
            f"Module: {module.code} "
            f"({'created' if module_created else 'updated'})"
        )
        self.stdout.write(
            f"Features synchronized: {len(features)} "
            f"({feature_created_count} new)"
        )
        self.stdout.write(
            f"Role-feature permissions synchronized: {role_feature_count}"
        )
        self.stdout.write(f"KPI widgets synchronized: {widget_count}")