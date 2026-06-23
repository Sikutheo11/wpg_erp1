from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from .models import (
    Project,
    Task,
    ConstructionMaterial,
    ConstructionLabour,
    ConstructionAssetUsage,
    ConstructionExpense
)
from inventory.models import RawMaterial
from Employee.models import Employee
from inventory.models import Asset



# =====================================================
# PROJECT MANAGEMENT
# =====================================================


@transaction.atomic
def create_project(
    name,
    client_name,
    start_date,
    budget=0,
    client_phone="",
    location="",
    manager=None
):

    project = Project.objects.create(

        name=name,

        client_name=client_name,

        client_phone=client_phone,

        location=location,

        start_date=start_date,

        budget=budget,

        manager=manager

    )

    return project



@transaction.atomic
def start_project(project):

    project.status = "ongoing"

    project.save(
        update_fields=[
            "status"
        ]
    )

    return project



@transaction.atomic
def pause_project(project):

    project.status = "paused"

    project.save(
        update_fields=[
            "status"
        ]
    )

    return project



@transaction.atomic
def complete_project(project):

    project.status = "completed"

    project.save(
        update_fields=[
            "status"
        ]
    )

    return project



@transaction.atomic
def cancel_project(project):

    project.status = "cancelled"

    project.save(
        update_fields=[
            "status"
        ]
    )

    return project




# =====================================================
# TASK MANAGEMENT
# =====================================================


def update_task_progress(
    task,
    progress
):

    task.progress = progress


    if progress >= 100:
        task.status = "done"

    elif progress > 0:
        task.status = "in_progress"


    task.save()

    return task



def complete_task(task):

    task.status = "done"

    task.progress = 100

    task.save()

    return task




# =====================================================
# MATERIAL MANAGEMENT
# =====================================================


@transaction.atomic
def add_material_usage(
    project,
    raw_material,
    quantity,
    unit_cost=None
):


    material = ConstructionMaterial.objects.create(

        project=project,

        raw_material=raw_material,

        quantity_used=quantity,

        unit_cost=(
            unit_cost
            or raw_material.unit_cost
        )

    )


    return material




# =====================================================
# LABOUR MANAGEMENT
# =====================================================


@transaction.atomic
def add_labour_cost(
    project,
    employee,
    role,
    hours,
    hourly_rate
):


    labour = ConstructionLabour.objects.create(

        project=project,

        employee=employee,

        role=role,

        hours_worked=hours,

        hourly_rate=hourly_rate

    )


    return labour




# =====================================================
# ASSET MANAGEMENT
# =====================================================


@transaction.atomic
def add_asset_usage(
    project,
    asset,
    hours,
    cost_per_hour
):


    usage = ConstructionAssetUsage.objects.create(

        project=project,

        asset=asset,

        hours_used=hours,

        cost_per_hour=cost_per_hour

    )


    return usage




# =====================================================
# FINANCIAL CONTROL
# =====================================================


def check_budget(project):

    return {

        "budget":
            project.budget,


        "spent":
            project.total_spent,


        "remaining":
            project.remaining_budget,


        "over_budget":
            project.total_spent >
            project.budget

    }



def get_project_financial_summary(project):


    return {


        "total_budget":
            project.budget,


        "material_cost":
            project.materials.aggregate(
                total=Sum('total_cost')
            )['total'] or Decimal("0"),


        "labour_cost":
            project.labours.aggregate(
                total=Sum('total_cost')
            )['total'] or Decimal("0"),


        "expense_cost":
            project.expenses.aggregate(
                total=Sum('amount')
            )['total'] or Decimal("0"),


        "asset_cost":
            project.asset_usage.aggregate(
                total=Sum('total_cost')
            )['total'] or Decimal("0"),


        "total_spent":
            project.total_spent,


        "remaining":
            project.remaining_budget

    }