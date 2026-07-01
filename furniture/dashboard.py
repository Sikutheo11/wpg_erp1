from .models import (
    Order,
    ProductionMaterial,
    ProductionOutput
)


def get_furniture_dashboard(user):


    # ==========================
    # CHECK EMPLOYEE PROFILE
    # ==========================

    if not hasattr(user, "employee"):

        return {
            "role": "no_employee",

            "title":
                "Employee Profile Required",

            "message":
                "Create employee profile to access dashboard",

            "kpis": {},

            "alerts": [
                "You don't have employee profile"
            ]
        }


    employee = user.employee



    # ==========================
    # CARPENTRY WORKER
    # ==========================

    if user.groups.filter(
        name="Carpentry Worker"
    ).exists():


        orders = Order.objects.filter(
            assigned_to=employee
        )


        return {

            "role":
                "worker",


            "title":
                "Carpentry Worker Dashboard",


            "kpis": {

                "my_orders":
                    orders.count(),


                "pending":
                    orders.exclude(
                        status="completed"
                    ).count(),


                "completed":
                    orders.filter(
                        status="completed"
                    ).count(),

            },


            "orders":
                orders,


            "alerts":[]

        }