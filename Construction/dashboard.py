from decimal import Decimal
from core.dashboard_registry import register_dashboard
from django.db.models import Sum, Avg, Count
from django.db.models.functions import Coalesce
from .models import (Project, ConstructionMaterial)



def get_construction_dashboard(user):

    projects = Project.objects.all()


    # ==========================
    # PROJECT KPI
    # ==========================

    project_summary = {

        "total":
            projects.count(),

        "planning":
            projects.filter(
                status="planning"
            ).count(),

        "ongoing":
            projects.filter(
                status="ongoing"
            ).count(),

        "completed":
            projects.filter(
                status="completed"
            ).count(),

        "delayed":
            projects.filter(
                status="delayed"
            ).count(),

        "average_progress":
        round(
            sum(
                p.progress_percentage
                for p in projects
            )
            /
            projects.count()
        )
        if projects.count()
        else 0

    }



    # ==========================
    # FINANCE
    # ==========================


    finance = {

        "total_budget":
            projects.aggregate(
                total=Coalesce(
                    Sum("budget"),
                    Decimal("0")
                )
            )["total"],



        "total_spent":
            sum(
                p.total_spent
                for p in projects
            )

    }


    finance["remaining"] = (
        finance["total_budget"]
        -
        finance["total_spent"]
    )


    if finance["total_budget"]:

        finance["utilization"] = (
            finance["total_spent"]
            /
            finance["total_budget"]
            *
            100
        )

    else:

        finance["utilization"] = 0



    # ==========================
    # BUDGET CHART
    # ==========================


    budget_chart = [

        {
            "name":p.name,

            "budget":
                float(p.budget),

            "spent":
                float(
                    p.total_spent
                )

        }

        for p in projects

    ]



    # ==========================
    # PROGRESS CHART
    # ==========================


    progress_chart=[

        {

        "name":p.name,

        "progress":
            p.progress_percentage

        }

        for p in projects

    ]



    # ==========================
    # MATERIAL ANALYSIS
    # ==========================


    material_chart = [

        {

        "name":
            x["raw_material__name"],


        "quantity":
            float(
                x["total"]
            )

        }

        for x in
        ConstructionMaterial.objects.values(
            "raw_material__name"
        )
        .annotate(
            total=Sum(
                "quantity_used"
            )
        )

    ]



    # ==========================
    # ALERT SYSTEM
    # ==========================


    alerts=[]


    for p in projects:


        if p.remaining_budget < 0:

            alerts.append({

                "level":"danger",

                "message":
                f"{p.name} exceeded budget"

            })


        if p.progress_percentage < 30 and p.status=="ongoing":

            alerts.append({

                "level":"warning",

                "message":
                f"{p.name} progress is low"

            })



    # ==========================
    # RETURN
    # ==========================


    return {


        "project_summary":
            project_summary,


        "finance":
            finance,


        "budget_chart":
            budget_chart,


        "progress_chart":
            progress_chart,


        "material_chart":
            material_chart,


        "alerts":
            alerts,


        "recent_projects":
            projects.order_by(
                "-created_at"
            )[:5]

    }

register_dashboard("construction", get_construction_dashboard)

print("Construction dashboard loaded")