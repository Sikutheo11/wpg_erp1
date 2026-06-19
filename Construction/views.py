from decimal import Decimal
from django.shortcuts import (render, redirect, get_object_or_404)
from django.contrib import messages
from django.db.models import Sum
from django.db.models.functions import Coalesce
from .models import (
    Project,
    Site,
    Task,
    ConstructionMaterial,
    ConstructionAssetUsage,
    ConstructionLabour,
    ConstructionExpense
)

from .forms import (
    ProjectForm,
    SiteForm,
    TaskForm,
    ConstructionMaterialForm,
    ConstructionAssetUsageForm,
    ConstructionLabourForm,
    ConstructionExpenseForm
)


# ======================================================
# DASHBOARD
# ======================================================

def construction_dashboard(request):

    projects = Project.objects.all()
    total_projects = projects.count()
    active_projects = projects.filter(
        status='ongoing'
    ).count()
    completed_projects = projects.filter(
        status='completed'
    ).count()
    delayed_projects = projects.filter(
        status='delayed'
    ).count()
    # ===============================
    # FINANCIAL DATA
    # ===============================
    total_budget = (
        projects.aggregate(
            total=Coalesce(
                Sum('budget'),
                Decimal('0')
            )
        )['total']
    )
    total_spent = sum(
        project.total_spent
        for project in projects
    )
    remaining_budget = (
        total_budget -
        total_spent
    )
    # ===============================
    # CHART DATA
    # ===============================
    budget_chart = []
    for project in projects:
        budget_chart.append({
            "name":
                project.name,
            "budget":
                float(project.budget),
            "spent":
                float(project.total_spent)

        })



    progress_chart = []
    for project in projects:
        progress_chart.append({
            "name":
                project.name,
            "progress":
                project.tasks.aggregate(
                    avg=Sum('progress')
                )['avg'] or 0

        })




    material_chart = []
    materials = (
        ConstructionMaterial.objects
        .values(
            'raw_material__name'
        )
        .annotate(
            total=Sum(
                'quantity_used'
            )
        )
    )


    for item in materials:
        material_chart.append({
            "name":
                item[
                    'raw_material__name'
                ],

            "quantity":
                float(
                    item['total']
                )

        })



    context = {
        "total_projects":total_projects,
        "active_projects": active_projects,
        "completed_projects":completed_projects,
        "delayed_projects": delayed_projects,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining_budget": remaining_budget,
        "budget_chart": budget_chart,
        "progress_chart": progress_chart,
        "material_chart": material_chart,
        "recent_projects": projects.order_by('-created_at')[:5]

    }

    return render(request, "construction/dashboard.html", context)


# ======================================================
# PROJECTS
# ======================================================

def project_list(request):

    projects = Project.objects.all()

    return render(
        request,
        'construction/projects/project_list.html',
        {
            'projects': projects
        }
    )


def project_create(request):

    form = ProjectForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            'Project created successfully'
        )

        return redirect(
            'project_list'
        )

    return render(
        request,
        'construction/projects/project_form.html',
        {
            'form': form
        }
    )


def project_detail(request, pk):

    project = get_object_or_404(
        Project,
        id=pk
    )

    context = {

        'project':
            project,

        'sites':
            project.sites.all(),

        'tasks':
            project.tasks.all(),

        'materials':
            project.materials.all(),

        'labours':
            project.labours.all(),

        'expenses':
            project.expenses.all(),

        'assets':
            project.asset_usage.all(),

    }

    return render(
        request,
        'construction/projects/project_detail.html',
        context
    )


def project_update(request, pk):

    project = get_object_or_404(
        Project,
        id=pk
    )

    form = ProjectForm(
        request.POST or None,
        instance=project
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            'Project updated'
        )

        return redirect(
            'project_list'
        )

    return render(
        request,
        'construction/projects/project_form.html',
        {
            'form': form
        }
    )


def project_delete(request, pk):

    project = get_object_or_404(
        Project,
        id=pk
    )

    if request.method == 'POST':

        project.delete()

        messages.success(
            request,
            'Project deleted'
        )

        return redirect(
            'project_list'
        )

    return render(
        request,
        'construction/projects/project_delete.html',
        {
            'project': project
        }
    )


# ======================================================
# SITES
# ======================================================

def site_list(request):

    sites = Site.objects.select_related(
        'project',
        'supervisor'
    )

    return render(
        request,
        'construction/sites/site_list.html',
        {
            'sites': sites
        }
    )


def site_create(request):

    form = SiteForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            'site_list'
        )

    return render(
        request,
        'construction/sites/site_form.html',
        {
            'form': form
        }
    )


# ======================================================
# TASKS
# ======================================================

def task_list(request):

    tasks = Task.objects.select_related(
        'project',
        'assigned_to'
    )

    return render(
        request,
        'construction/tasks/task_list.html',
        {
            'tasks': tasks
        }
    )


def task_create(request):

    form = TaskForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            'task_list'
        )

    return render(
        request,
        'construction/tasks/task_form.html',
        {
            'form': form
        }
    )


# ======================================================
# MATERIAL USAGE
# ======================================================

def material_usage_list(request):

    materials = (
        ConstructionMaterial.objects
        .select_related(
            'project',
            'raw_material'
        )
    )

    return render(
        request,
        'inventory/materials/material_usage_list.html',
        {
            'materials': materials
        }
    )


def material_usage_create(request):

    form = ConstructionMaterialForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            'Material usage recorded'
        )

        return redirect(
            'material_usage_list'
        )

    return render(
        request,
        'inventory/materials/material_usage_form.html',
        {
            'form': form
        }
    )


# ======================================================
# ASSET USAGE
# ======================================================

def asset_usage_list(request):

    assets = (
        ConstructionAssetUsage.objects
        .select_related(
            'project',
            'asset'
        )
    )

    return render(
        request,
        'inventory/assets/asset_usage_list.html',
        {
            'assets': assets
        }
    )


def asset_usage_create(request):

    form = ConstructionAssetUsageForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            'asset_usage_list'
        )

    return render(
        request,
        'inventory/assets/asset_usage_form.html',
        {
            'form': form
        }
    )


# ======================================================
# LABOUR
# ======================================================

def labour_list(request):

    labours = (
        ConstructionLabour.objects
        .select_related(
            'project',
            'employee'
        )
    )

    return render(
        request,
        'labour/labour_list.html',
        {
            'labours': labours
        }
    )


def labour_create(request):

    form = ConstructionLabourForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            'labour_list'
        )

    return render(
        request,
        'labour/labour_form.html',
        {
            'form': form
        }
    )


# ======================================================
# EXPENSES
# ======================================================

def expense_list(request):

    expenses = (
        ConstructionExpense.objects
        .select_related('project')
    )

    return render(
        request,
        'finance/expenses/expense_list.html',
        {
            'expenses': expenses
        }
    )


def expense_create(request):

    form = ConstructionExpenseForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            'expense_list'
        )

    return render(
        request,
        'finance/expenses/expense_form.html',
        {
            'form': form
        }
    )


# ======================================================
# REPORTS
# ======================================================

def project_cost_report(request):

    projects = Project.objects.all()

    return render(
        request,
        'reports/project_cost_report.html',
        {
            'projects': projects
        }
    )