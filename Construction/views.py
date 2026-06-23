# Construction/views.py


from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages

from django.contrib.auth.decorators import (
    login_required,
    permission_required
)


from .dashboard import get_construction_dashboard


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

@login_required
def construction_dashboard(request):

    context = get_construction_dashboard()

    return render(
        request,
        "construction/dashboard.html",
        context
    )



# ======================================================
# PROJECTS
# ======================================================

@login_required
@permission_required(
    "construction.view_project",
    raise_exception=True
)
def project_list(request):

    projects = Project.objects.all().order_by(
        "-created_at"
    )

    return render(
        request,
        "construction/project_list.html",
        {
            "projects": projects
        }
    )



@login_required
@permission_required(
    "construction.add_project",
    raise_exception=True
)
def project_create(request):

    if request.method == "POST":

        form = ProjectForm(
            request.POST
        )

        if form.is_valid():

            project = form.save()


            messages.success(
                request,
                "Project created successfully"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )

    else:

        form = ProjectForm()


    return render(
        request,
        "construction/project_form.html",
        {
            "form": form
        }
    )



@login_required
@permission_required(
    "construction.view_project",
    raise_exception=True
)
def project_detail(request, pk):

    project = get_object_or_404(
        Project,
        pk=pk
    )


    return render(
        request,
        "construction/project_detail.html",
        {
            "project": project
        }
    )



@login_required
@permission_required(
    "construction.change_project",
    raise_exception=True
)
def project_update(request, pk):

    project = get_object_or_404(
        Project,
        pk=pk
    )


    if request.method == "POST":

        form = ProjectForm(
            request.POST,
            instance=project
        )


        if form.is_valid():

            form.save()


            messages.success(
                request,
                "Project updated successfully"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = ProjectForm(
            instance=project
        )


    return render(
        request,
        "construction/project_form.html",
        {
            "form": form
        }
    )



# ======================================================
# SITE
# ======================================================

@login_required
@permission_required(
    "construction.add_site",
    raise_exception=True
)
def site_create(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id
    )


    if request.method == "POST":

        form = SiteForm(
            request.POST
        )


        if form.is_valid():

            site = form.save(
                commit=False
            )

            site.project = project

            site.save()


            messages.success(
                request,
                "Site created successfully"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = SiteForm()


    return render(
        request,
        "construction/site_form.html",
        {
            "form": form,
            "project": project
        }
    )



# ======================================================
# TASK
# ======================================================

@login_required
@permission_required(
    "construction.add_task",
    raise_exception=True
)
def task_create(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id
    )


    if request.method == "POST":

        form = TaskForm(
            request.POST
        )


        if form.is_valid():

            task = form.save(
                commit=False
            )

            task.project = project

            task.save()


            messages.success(
                request,
                "Task created successfully"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = TaskForm()


    return render(
        request,
        "construction/task_form.html",
        {
            "form": form,
            "project": project
        }
    )



# ======================================================
# MATERIAL
# ======================================================

@login_required
@permission_required(
    "construction.add_constructionmaterial",
    raise_exception=True
)
def material_create(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id
    )


    if request.method == "POST":

        form = ConstructionMaterialForm(
            request.POST
        )


        if form.is_valid():

            material = form.save(
                commit=False
            )

            material.project = project

            material.save()


            messages.success(
                request,
                "Material usage recorded"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = ConstructionMaterialForm()


    return render(
        request,
        "construction/material_form.html",
        {
            "form": form,
            "project": project
        }
    )



# ======================================================
# LABOUR
# ======================================================

@login_required
@permission_required(
    "construction.add_constructionlabour",
    raise_exception=True
)
def labour_create(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id
    )


    if request.method == "POST":

        form = ConstructionLabourForm(
            request.POST
        )


        if form.is_valid():

            labour = form.save(
                commit=False
            )

            labour.project = project

            labour.save()


            messages.success(
                request,
                "Labour recorded"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = ConstructionLabourForm()


    return render(
        request,
        "construction/labour_form.html",
        {
            "form": form,
            "project": project
        }
    )



# ======================================================
# ASSET USAGE
# ======================================================

@login_required
@permission_required(
    "construction.add_constructionassetusage",
    raise_exception=True
)
def asset_usage_create(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id
    )


    if request.method == "POST":

        form = ConstructionAssetUsageForm(
            request.POST
        )


        if form.is_valid():

            usage = form.save(
                commit=False
            )

            usage.project = project

            usage.save()


            messages.success(
                request,
                "Asset usage recorded"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = ConstructionAssetUsageForm()


    return render(
        request,
        "construction/asset_usage_form.html",
        {
            "form": form,
            "project": project
        }
    )



# ======================================================
# EXPENSE
# ======================================================

@login_required
@permission_required(
    "construction.add_constructionexpense",
    raise_exception=True
)
def expense_create(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id
    )


    if request.method == "POST":

        form = ConstructionExpenseForm(
            request.POST
        )


        if form.is_valid():

            expense = form.save(
                commit=False
            )

            expense.project = project

            expense.save()


            messages.success(
                request,
                "Expense recorded"
            )


            return redirect(
                "construction:project_detail",
                pk=project.id
            )


    else:

        form = ConstructionExpenseForm()


    return render(
        request,
        "construction/expense_form.html",
        {
            "form": form,
            "project": project
        }
    )