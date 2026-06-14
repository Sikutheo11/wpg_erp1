from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count
from finance.models import Income, Expense, Receivable, Payable
from inventory.models import RawMaterial, Asset, Product
from furniture.models import Order
from Construction.models import Project
from Employee.models import Employee, Contact, Department, Position
from django.utils import timezone
from .models import *
from datetime import date, datetime


def construction_dashboard(request):

    # =========================
    # BASIC KPIs
    # =========================
    total_projects = Project.objects.count()

    active_projects = Project.objects.filter(
        status='ongoing'
    ).count()

    active_sites = Site.objects.filter(
        project__status='ongoing'
    ).count()

    # =========================
    # BUDGET VS SPENT
    # =========================
    projects = Project.objects.all()

    total_budget = projects.aggregate(total=Sum('budget'))['total'] or 0
    total_spent = sum(p.total_spent for p in projects)

    # =========================
    # PROFIT ESTIMATION
    # (simple model: budget - spent)
    # =========================
    estimated_profit = total_budget - total_spent

    # =========================
    # DELAY DETECTION
    # projects past end_date but not completed
    # =========================
    delayed_projects = Project.objects.filter(
        end_date__lt=date.today()
    ).exclude(status='completed')

    delayed_count = delayed_projects.count()

    # =========================
    # WORKFORCE PRODUCTIVITY SCORE
    # =========================
    labour = ConstructionLabour.objects.all()

    total_hours = labour.aggregate(total=Sum('hours_worked'))['total'] or 0
    total_cost = labour.aggregate(total=Sum('total_cost'))['total'] or 0

    # simple productivity model:
    # productivity = cost efficiency (lower cost per hour = better)
    productivity_score = 0
    if total_hours > 0:
        productivity_score = round(total_cost / total_hours, 2)

    # =========================
    # CHART DATA (Budget vs Spent per project)
    # =========================
    chart_data = [
        {
            "project": p.name,
            "budget": float(p.budget),
            "spent": float(p.total_spent),
        }
        for p in projects
    ]

    # =========================
    # CONTEXT
    # =========================
    context = {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "active_sites": active_sites,

        "total_budget": total_budget,
        "total_spent": total_spent,

        "estimated_profit": estimated_profit,

        "delayed_count": delayed_count,

        "productivity_score": productivity_score,

        "chart_data": chart_data,
    }

    return render(request, "construction/manager_dashboard.html", context)