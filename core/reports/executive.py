from core.report_engine import ReportEngine

from core.providers.finance_provider import FinanceProvider
from core.providers.inventory_provider import InventoryProvider
from core.providers.furniture_provider import FurnitureProvider
from core.providers.construction_provider import ConstructionProvider
from core.providers.agriculture_provider import AgricultureProvider
from core.providers.marketplace_provider import MarketplaceProvider
from core.providers.order_provider import OrderProvider
from core.providers.people_provider import PeopleProvider


def generate(user=None, **kwargs):

    summary = [
        {
            "title": "Financial Performance",
            "items": [
                {
                    "label": "Total Income",
                    "value": FinanceProvider.total_income(),
                },
                {
                    "label": "Total Expenses",
                    "value": FinanceProvider.total_expense(),
                },
                {
                    "label": "Net Profit",
                    "value": FinanceProvider.net_profit(),
                },
            ],
        },

        {
            "title": "Operations",
            "items": [
                {
                    "label": "Total Orders",
                    "value": OrderProvider.total_orders(),
                },
                {
                    "label": "Pending Orders",
                    "value": OrderProvider.pending_orders(),
                },
                {
                    "label": "Active Production Jobs",
                    "value": FurnitureProvider.active_jobs(),
                },
                {
                    "label": "Completed Outputs",
                    "value": FurnitureProvider.completed_outputs(),
                },
            ],
        },

        {
            "title": "Construction",
            "items": [
                {
                    "label": "Active Projects",
                    "value": ConstructionProvider.active_projects(),
                },
                {
                    "label": "Delayed Projects",
                    "value": ConstructionProvider.delayed_projects(),
                },
                {
                    "label": "Budget Used",
                    "value": ConstructionProvider.budget_used(),
                },
            ],
        },

        {
            "title": "Inventory",
            "items": [
                {
                    "label": "Products",
                    "value": InventoryProvider.products(),
                },
                {
                    "label": "Raw Materials",
                    "value": InventoryProvider.raw_materials(),
                },
                {
                    "label": "Stock Alerts",
                    "value": InventoryProvider.stock_alerts(),
                },
            ],
        },

        {
            "title": "People",
            "items": [
                {
                    "label": "Employees",
                    "value": PeopleProvider.employees(),
                },
                {
                    "label": "Attendance Today",
                    "value": PeopleProvider.attendance_today(),
                },
            ],
        },

        {
            "title": "Agriculture & Poultry",
            "items": [
                {
                    "label": "Egg Production",
                    "value": AgricultureProvider.egg_production(),
                },
                {
                    "label": "Mortality",
                    "value": AgricultureProvider.mortality(),
                },
                {
                    "label": "Poultry Batches",
                    "value": AgricultureProvider.poultry_batches(),
                },
                {
                    "label": "Feed Consumption",
                    "value": AgricultureProvider.feed_consumption(),
                },
            ],
        },

        {
            "title": "Marketplace",
            "items": [
                {
                    "label": "Online Orders",
                    "value": MarketplaceProvider.online_orders(),
                },
                {
                    "label": "Online Products",
                    "value": MarketplaceProvider.online_products(),
                },
            ],
        },
    ]

    return ReportEngine.build_report(
        title="Executive Report",
        code="EXECUTIVE_REPORT",
        generated_by=user,
        summary=summary,
        rows=[],
        charts={},
    )