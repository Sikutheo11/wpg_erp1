# sales/dashboard.py

from .services import get_sales_summary


def get_sales_dashboard(user=None):
    summary = get_sales_summary(user=user)

    return {

        # ==========================================
        # CUSTOMERS
        # ==========================================

        "total_customers": summary["total_customers"],

        # ==========================================
        # QUOTATIONS
        # ==========================================

        "total_quotations": summary["total_quotations"],
        "draft_quotations": summary["draft_quotations"],
        "sent_quotations": summary["sent_quotations"],
        "approved_quotations": summary["approved_quotations"],
        "converted_quotations": summary["converted_quotations"],
        "open_quotations": summary["open_quotations"],

        # ==========================================
        # ORDERS
        # ==========================================

        "total_orders": summary["total_orders"],
        "monthly_orders": summary["monthly_orders"],

        # ==========================================
        # SALES PERFORMANCE
        # ==========================================

        "monthly_sales": summary["monthly_sales"],
        "conversion_rate": summary["conversion_rate"],

        # ==========================================
        # RECENT ACTIVITY
        # ==========================================

        "recent_quotations": summary["recent_quotations"],
        "recent_orders": summary["recent_orders"],
    }