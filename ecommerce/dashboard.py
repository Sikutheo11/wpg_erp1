# ecommerce/dashboard.py


from django.db.models import Sum
from django.utils import timezone

from core.dashboard_registry import register_dashboard




def get_ecommerce_dashboard(user):


    data = {}



    # ======================================
    # ONLINE PRODUCTS KPI
    # ======================================

    try:

        from .models import OnlineProduct


        data["products"] = {

            "total":
                OnlineProduct.objects.count(),


            "published":
                OnlineProduct.objects.filter(
                    is_published=True
                ).count(),


            "featured":
                OnlineProduct.objects.filter(
                    is_featured=True
                ).count(),

        }



    except Exception:


        data["products"] = {

            "total": 0,

            "published": 0,

            "featured": 0,

        }





    # ======================================
    # PRODUCT VIEWS KPI
    # ======================================

    try:

        from .models import OnlineProduct


        total_views = (
            OnlineProduct.objects.aggregate(
                total=Sum("views")
            )["total"] or 0
        )


        data["views"] = total_views



    except Exception:


        data["views"] = 0





    # ======================================
    # FEATURED PRODUCTS
    # ======================================

    try:

        from .models import OnlineProduct


        data["featured_products"] = (
            OnlineProduct.objects.filter(
                is_featured=True
            ).count()
        )


    except Exception:


        data["featured_products"] = 0





    # ======================================
    # SYSTEM INFO
    # ======================================

    data["generated_at"] = timezone.now()



    return data






# ======================================
# REGISTER DASHBOARD
# ======================================


register_dashboard(
    "ecommerce",
    get_ecommerce_dashboard
)