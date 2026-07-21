from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/read-all/", views.notification_mark_all_read, name="notification_mark_all_read"),
    path("audit-logs/", views.audit_log_list, name="audit_log_list"),
    path("reports/", views.reports_home, name="reports_home"),
    path("reports/executive/", views.executive_report, name="executive_report"),
    path("reports/finance/", views.finance_report, name="finance_report"),
    path("reports/inventory/", views.inventory_report, name="inventory_report"),
    path("reports/furniture/", views.furniture_report, name="furniture_report"),
    path("reports/construction/", views.construction_report, name="construction_report"),
    path("reports/agriculture/", views.agriculture_report, name="agriculture_report"),
    path("reports/marketplace/", views.marketplace_report, name="marketplace_report"),
]