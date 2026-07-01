# sales/dashboard.py


from .services import get_sales_summary



def get_sales_dashboard(user):

    summary = get_sales_summary()


    return {

        # ==========================
        # CUSTOMERS
        # ==========================

        "total_customers":
            summary["total_customers"],


        # ==========================
        # QUOTATIONS
        # ==========================

        "total_quotations":
            summary["total_quotations"],


        # ==========================
        # SALES
        # ==========================

        "total_sales":
            summary["total_sales"],


        "total_sales_amount":
            summary["total_sales_amount"],


        # ==========================
        # INVOICES
        # ==========================

        "total_invoices":
            summary["total_invoices"],


        "total_invoice_amount":
            summary["total_invoice_amount"],


        "total_paid_amount":
            summary["total_paid_amount"],


        "outstanding_amount":
            summary["outstanding_amount"],


        # ==========================
        # PAYMENTS
        # ==========================

        "total_payments":
            summary.get(
                "total_payments",
                0
            ),


        # ==========================
        # RECENT SALES
        # ==========================

        "recent_sales":
            summary["recent_sales"],

    }