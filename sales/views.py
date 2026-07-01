# sales/views.py


from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .dashboard import get_sales_dashboard

from .models import (
    Customer,
    SalesQuotation,
    SalesQuotationItem,
    Sale,
    SaleItem,
    Invoice,
    CustomerPayment,
)

from .services import (
    complete_sale,
    prepare_sale,
    prepare_quotation,
)



# =====================================================
# DASHBOARD
# =====================================================


@login_required
def sales_dashboard(request):

    context = get_sales_dashboard(
        request.user
    )

    return render(
        request,
        "sales/dashboard.html",
        context
    )



# =====================================================
# CUSTOMER MANAGEMENT
# =====================================================


@login_required
def customer_list(request):

    customers = Customer.objects.all()

    return render(
        request,
        "sales/customers/customer_list.html",
        {
            "customers": customers
        }
    )



@login_required
def customer_detail(request, pk):

    customer = get_object_or_404(
        Customer,
        id=pk
    )

    return render(
        request,
        "sales/customers/customer_detail.html",
        {
            "customer": customer
        }
    )



@login_required
def customer_create(request):

    # form izaza hano

    return render(
        request,
        "sales/customers/customer_form.html"
    )



@login_required
def customer_update(request, pk):

    customer = get_object_or_404(
        Customer,
        id=pk
    )

    return render(
        request,
        "sales/customers/customer_form.html",
        {
            "customer": customer
        }
    )



@login_required
def customer_delete(request, pk):

    customer = get_object_or_404(
        Customer,
        id=pk
    )

    if request.method == "POST":

        customer.delete()

        messages.success(
            request,
            "Customer deleted successfully"
        )

        return redirect(
            "customer_list"
        )


    return render(
        request,
        "sales/customers/customer_delete.html",
        {
            "customer": customer
        }
    )



# =====================================================
# QUOTATIONS
# =====================================================


@login_required
def quotation_list(request):

    quotations = (
        SalesQuotation.objects
        .order_by("-created_at")
    )


    return render(
        request,
        "sales/quotations/quotation_list.html",
        {
            "quotations": quotations
        }
    )



@login_required
def quotation_detail(request, pk):

    quotation = get_object_or_404(
        SalesQuotation,
        id=pk
    )

    return render(
        request,
        "sales/quotations/quotation_detail.html",
        {
            "quotation": quotation
        }
    )



@login_required
def quotation_create(request):

    quotation = SalesQuotation()

    quotation = prepare_quotation(
        quotation
    )


    return redirect(
        "quotation_detail",
        pk=quotation.id
    )



# =====================================================
# SALES
# =====================================================


@login_required
def sale_list(request):

    sales = (
        Sale.objects
        .order_by("-created_at")
    )


    return render(
        request,
        "sales/sales/sale_list.html",
        {
            "sales": sales
        }
    )



@login_required
def sale_detail(request, pk):

    sale = get_object_or_404(
        Sale,
        id=pk
    )


    return render(
        request,
        "sales/sales/sale_detail.html",
        {
            "sale": sale
        }
    )



@login_required
def complete_sale_view(request, pk):

    sale = get_object_or_404(
        Sale,
        id=pk
    )


    if request.method == "POST":

        complete_sale(
            sale,
            request.user
        )


        messages.success(
            request,
            "Sale completed successfully"
        )


    return redirect(
        "sale_detail",
        pk=sale.id
    )



# =====================================================
# INVOICE
# =====================================================


@login_required
def invoice_list(request):

    invoices = Invoice.objects.all()


    return render(
        request,
        "sales/invoices/invoice_list.html",
        {
            "invoices": invoices
        }
    )



@login_required
def invoice_detail(request, pk):

    invoice = get_object_or_404(
        Invoice,
        id=pk
    )


    return render(
        request,
        "sales/invoices/invoice_detail.html",
        {
            "invoice": invoice
        }
    )



# =====================================================
# CUSTOMER PAYMENTS
# =====================================================


@login_required
def payment_list(request):

    payments = (
        CustomerPayment.objects
        .order_by("-payment_date")
    )


    return render(
        request,
        "sales/payments/payment_list.html",
        {
            "payments": payments
        }
    )



# =====================================================
# REPORTS
# =====================================================


@login_required
def sales_report(request):

    sales = Sale.objects.all()


    return render(
        request,
        "sales/reports/sales_report.html",
        {
            "sales": sales
        }
    )