from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone



def get_dashboard_charts(user):

    charts = {}



    # ==================================
    # SALES TREND CHART
    # ==================================

    try:

        from sales.models import Sale


        sales = (
            Sale.objects
            .annotate(
                month=TruncMonth("created_at")
            )
            .values("month")
            .annotate(
                total=Sum("total_amount")
            )
            .order_by("month")
        )


        charts["sales_trend"] = {

            "labels":[
                item["month"].strftime("%b %Y")
                for item in sales
                if item["month"]
            ],


            "data":[
                float(item["total"] or 0)
                for item in sales
            ]

        }



    except Exception as e:

        charts["sales_trend"] = {

            "labels":[],
            "data":[]

        }





    # ==================================
    # PROFIT ANALYSIS
    # ==================================

    try:

        from finance.models import Income, Expense


        income = (
            Income.objects
            .aggregate(
                total=Sum("amount")
            )
            ["total"] or 0
        )


        expense = (
            Expense.objects
            .aggregate(
                total=Sum("amount")
            )
            ["total"] or 0
        )


        charts["profit"] = {


            "income":
                float(income),


            "expense":
                float(expense),


            "profit":
                float(
                    income-expense
                )

        }



    except Exception:


        charts["profit"] = {

            "income":0,
            "expense":0,
            "profit":0

        }





    # ==================================
    # INVENTORY STATUS
    # ==================================

    try:

        from inventory.models import Product


        charts["inventory"] = {


            "products":
                Product.objects.count()


        }



    except Exception:


        charts["inventory"] = {


            "products":0

        }





    # ==================================
    # SYSTEM
    # ==================================

    charts["generated_at"] = timezone.now()


    return charts