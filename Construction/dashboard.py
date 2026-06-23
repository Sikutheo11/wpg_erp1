# Construction/dashboard.py

from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import (
    Project,
    ConstructionMaterial,
)



# ======================================================
# CONSTRUCTION DASHBOARD DATA
# ======================================================


def get_construction_dashboard():

    projects = Project.objects.all()



    # ==================================================
    # PROJECT SUMMARY
    # ==================================================

    total_projects = projects.count()


    planning_projects = projects.filter(
        status="planning"
    ).count()


    ongoing_projects = projects.filter(
        status="ongoing"
    ).count()


    paused_projects = projects.filter(
        status="paused"
    ).count()


    completed_projects = projects.filter(
        status="completed"
    ).count()


    cancelled_projects = projects.filter(
        status="cancelled"
    ).count()


    delayed_projects = projects.filter(
        status="delayed"
    ).count()



    # ==================================================
    # FINANCIAL SUMMARY
    # ==================================================

    total_budget = projects.aggregate(
        total=Coalesce(
            Sum("budget"),
            Decimal("0")
        )
    )["total"]



    total_spent = sum(
        project.total_spent
        for project in projects
    )



    remaining_budget = (
        total_budget -
        total_spent
    )



    # ==================================================
    # BUDGET VS SPENDING CHART
    # ==================================================

    budget_chart = []


    for project in projects:

        budget_chart.append({

            "name":
                project.name,


            "budget":
                float(
                    project.budget
                ),


            "spent":
                float(
                    project.total_spent
                )

        })



    # ==================================================
    # PROJECT PROGRESS CHART
    # ==================================================

    progress_chart = []


    for project in projects:

        progress_chart.append({

            "name":
                project.name,


            "progress":
                project.progress_percentage

        })



    # ==================================================
    # MATERIAL USAGE CHART
    # ==================================================

    material_chart = []


    materials = (

        ConstructionMaterial.objects

        .values(
            "raw_material__name"
        )

        .annotate(

            total_quantity=
                Sum(
                    "quantity_used"
                )

        )

    )


    for item in materials:


        material_chart.append({

            "name":
                item[
                    "raw_material__name"
                ],


            "quantity":
                float(
                    item[
                        "total_quantity"
                    ]
                )

        })



    # ==================================================
    # PROJECT ALERTS
    # ==================================================

    alerts = []


    for project in projects:


        if project.remaining_budget < 0:

            alerts.append({

                "type":
                    "budget",

                "message":
                    f"{project.name} exceeded budget"

            })



        if project.status == "delayed":

            alerts.append({

                "type":
                    "delay",

                "message":
                    f"{project.name} is delayed"

            })



    # ==================================================
    # RECENT PROJECTS
    # ==================================================

    recent_projects = (
        projects
        .order_by(
            "-created_at"
        )[:5]
    )



    # ==================================================
    # RETURN DASHBOARD DATA
    # ==================================================

    return {


        # Projects

        "total_projects":
            total_projects,


        "planning_projects":
            planning_projects,


        "ongoing_projects":
            ongoing_projects,


        "paused_projects":
            paused_projects,


        "completed_projects":
            completed_projects,


        "cancelled_projects":
            cancelled_projects,


        "delayed_projects":
            delayed_projects,



        # Finance

        "total_budget":
            total_budget,


        "total_spent":
            total_spent,


        "remaining_budget":
            remaining_budget,



        # Charts

        "budget_chart":
            budget_chart,


        "progress_chart":
            progress_chart,


        "material_chart":
            material_chart,



        # Alerts

        "alerts":
            alerts,



        # Recent

        "recent_projects":
            recent_projects,

    }