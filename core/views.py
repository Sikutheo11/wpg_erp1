from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .dashboard import DashboardService
from .models import Notification, AuditLog
from .report_engine import ReportEngine
from .executive_dashboard import ExecutiveDashboard


# =====================================================
# HOME / DASHBOARDS
# =====================================================

def home(request):
    return render(request, "core/home.html")


@login_required
def customer_dashboard(request):
    return render(request, "accounts/customer_dashboard.html")

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
# REPORTS
# =====================================================

@login_required
def reports_home(request):
    reports = ReportEngine.all_reports()

    return render(
        request,
        "core/reports_home.html",
        {
            "reports": reports
        }
    )


@login_required
def executive_report(request):
    report = ReportEngine.generate("EXECUTIVE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
def finance_report(request):
    report = ReportEngine.generate("FINANCE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
def inventory_report(request):
    report = ReportEngine.generate("INVENTORY", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
def furniture_report(request):
    report = ReportEngine.generate("FURNITURE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
def construction_report(request):
    report = ReportEngine.generate("CONSTRUCTION", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
def agriculture_report(request):
    report = ReportEngine.generate("AGRICULTURE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})


@login_required
def marketplace_report(request):
    report = ReportEngine.generate("MARKETPLACE", user=request.user)
    return render(request, "core/report_detail.html", {"report": report})