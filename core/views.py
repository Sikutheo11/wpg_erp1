from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .dashboard import DashboardService
from .models import Notification, AuditLog, ApprovalRequest
from .report_engine import ReportEngine
from .executive_dashboard import ExecutiveDashboard
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import connection
from django.db.utils import DatabaseError
from ecommerce.models import OnlineProduct
from .permissions import PermissionService, wpg_permission_required


# =====================================================
# HOME / DASHBOARDS
# =====================================================
def health_check(request):
    """
    Public deployment health check.

    It exposes no credentials or business data. A healthy response means
    that Django is running and PostgreSQL accepts queries.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            database_ok = cursor.fetchone()[0] == 1
    except DatabaseError:
        database_ok = False

    if database_ok:
        return JsonResponse(
            {
                "status": "ok",
                "database": "ok",
            },
            status=200,
        )

    return JsonResponse(
        {
            "status": "unavailable",
            "database": "unavailable",
        },
        status=503,
    )


def home(request):
    catalogue = (
        OnlineProduct.objects
        .select_related(
            "product",
            "product__category",
        )
        .filter(
            product__is_active=True,
            product__is_published=True,
        )
    )

    featured_products = list(
        catalogue
        .filter(product__is_featured=True)
        .order_by(
            "product__business_unit",
            "product__name",
        )[:8]
    )

    # A new marketplace may not yet have featured products.
    # Show the newest published products instead of an empty homepage.
    if not featured_products:
        featured_products = list(
            catalogue.order_by("-created_at")[:8]
        )

    context = {
        "featured_products": featured_products,
        "published_product_count": catalogue.count(),
    }

    return render(
        request,
        "core/home.html",
        context,
    )


@login_required
def customer_dashboard(request):
    return redirect("ecommerce:shop")

@login_required
def dashboard(request):
    context = DashboardService.get_dashboard_context(
        request.user
    )

    executive_context = ExecutiveDashboard.get_context(
        request.user
    )

    context.update(executive_context)

    return render(
        request,
        "core/dashboard.html",
        context
    )

# =====================================================
# NOTIFICATIONS
# =====================================================

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "core/notifications.html",
        {
            "notifications": notifications
        }
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(
        Notification,
        id=pk,
        user=request.user
    )

    notification.is_read = True
    notification.save()

    if notification.url:
        return redirect(notification.url)

    return redirect("core:notification_list")


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect("core:notification_list")


# =====================================================
# AUDIT
# =====================================================

@login_required
@wpg_permission_required(
    "core.view_auditlog",
    feature_code="AUDIT_LOGS",
)
def audit_log_list(request):
    logs = AuditLog.objects.select_related(
        "user"
    ).order_by("-created_at")

    return render(
        request,
        "core/audit_logs.html",
        {
            "logs": logs
        }
    )


# =====================================================
# APPROVAL REGISTER
# =====================================================

@login_required
@wpg_permission_required(
    "core.view_approvalrequest",
    feature_code="APPROVAL_PENDING",
)
def approval_request_list(request):
    selected_status = request.GET.get("status", "PENDING").upper()
    approvals = ApprovalRequest.objects.select_related(
        "requested_by", "approved_by"
    )
    if selected_status != "ALL":
        approvals = approvals.filter(status=selected_status)
    return render(
        request,
        "core/approval_request_list.html",
        {
            "approvals": approvals,
            "selected_status": selected_status,
            "status_choices": ApprovalRequest.STATUS_CHOICES,
        },
    )


# =====================================================
# REPORTS
# =====================================================

@login_required
def reports_home(request):
    feature_by_report = {
        "EXECUTIVE": "REPORTING_EXECUTIVE_DASHBOARD",
        "FINANCE": "FINANCE_REPORTS",
        "INVENTORY": "INVENTORY_REPORTS",
        "FURNITURE": "FURNITURE_REPORTS",
        "CONSTRUCTION": "CONSTRUCTION_REPORTS",
        "AGRICULTURE": "AGRICULTURE_REPORTS",
        "MARKETPLACE": "MARKETPLACE_REPORTS",
    }
    reports = [
        report
        for report in ReportEngine.all_reports()
        if PermissionService.user_can_access_feature(
            request.user,
            feature_by_report.get(report.code, "REPORTING_REPORTS"),
            action="view",
        )
    ]

    return render(
        request,
        "core/reports_home.html",
        {
            "reports": reports
        }
    )


@login_required
@wpg_permission_required(
    "core.view_executivereport",
    feature_code="REPORTING_EXECUTIVE_DASHBOARD",
)
def executive_report(request):
    report = ReportEngine.generate("EXECUTIVE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
@wpg_permission_required(
    "finance.view_transaction",
    feature_code="FINANCE_REPORTS",
)
def finance_report(request):
    report = ReportEngine.generate("FINANCE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
@wpg_permission_required(
    "inventory.view_product",
    feature_code="INVENTORY_REPORTS",
)
def inventory_report(request):
    report = ReportEngine.generate("INVENTORY", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
@wpg_permission_required(
    "furniture.view_productionjob",
    feature_code="FURNITURE_REPORTS",
)
def furniture_report(request):
    report = ReportEngine.generate("FURNITURE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
@wpg_permission_required(
    "Construction.view_project",
    feature_code="CONSTRUCTION_REPORTS",
)
def construction_report(request):
    report = ReportEngine.generate("CONSTRUCTION", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
@wpg_permission_required(
    "agriculture.view_agricultureoperation",
    feature_code="AGRICULTURE_REPORTS",
)
def agriculture_report(request):
    report = ReportEngine.generate("AGRICULTURE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
@wpg_permission_required(
    "ecommerce.view_marketplaceorderline",
    feature_code="MARKETPLACE_REPORTS",
)
def marketplace_report(request):
    report = ReportEngine.generate("MARKETPLACE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})
