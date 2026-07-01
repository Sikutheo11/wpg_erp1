from django.db.models import Sum
from django.utils import timezone

from .permissions import EXECUTIVE_PERMISSIONS



def has_permission(user, permission):

    if user.is_superuser:
        return True

    return user.has_perm(permission)




def get_executive_dashboard(user):

    data = {}



    # ==========================
    # SALES CARD
    # ==========================

    if has_permission(
        user,
        EXECUTIVE_PERMISSIONS["sales"]["card"]
    ):

        from sales.models import Sale


        data["sales"] = {

            "total_sales":
                Sale.objects.count(),


            "sales_amount":
                Sale.objects.aggregate(
                    total=Sum("total_amount")
                )["total"] or 0,


            "completed_sales":
                Sale.objects.filter(
                    status__iexact="completed"
                ).count(),

        }



    # ==========================
    # FINANCE CARD
    # ==========================

    if has_permission(
        user,
        EXECUTIVE_PERMISSIONS["finance"]["card"]
    ):

        from finance.models import Income, Expense


        income = (
            Income.objects.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )


        expense = (
            Expense.objects.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )


        data["finance"] = {

            "income":
                income,


            "expense":
                expense,


            "profit":
                income - expense,

        }




    # ==========================
    # INVENTORY CARD
    # ==========================

    if has_permission(
        user,
        EXECUTIVE_PERMISSIONS["inventory"]["card"]
    ):

        from inventory.models import Product


        data["inventory"] = {

            "products":
                Product.objects.count(),

        }




    # ==========================
    # HR CARD
    # ==========================

    if has_permission(
        user,
        EXECUTIVE_PERMISSIONS["hr"]["card"]
    ):

        from Employee.models import Employee


        data["hr"] = {

            "employees":
                Employee.objects.count(),

        }




    # ==========================
    # CONSTRUCTION CARD
    # ==========================

    if has_permission(
        user,
        EXECUTIVE_PERMISSIONS["construction"]["card"]
    ):

        from Construction.models import Project


        data["construction"] = {

            "projects":
                Project.objects.count(),

        }




    # ==========================
    # SYSTEM INFO
    # ==========================

    data["generated_at"] = timezone.now()


    return data