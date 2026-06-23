from django.shortcuts import (render,redirect, get_object_or_404)
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import (Sum, Count, F, ExpressionWrapper, DecimalField)
from .models import (
    Customer,
    Sale,
    SalesQuotation,
    Invoice,
    CustomerPayment,
)
from .forms import (
    CustomerForm,
    SaleForm,
    SaleItemFormSet,
    SalesQuotationForm,
    CustomerPaymentForm,
)
from .pdf import generate_invoice_pdf


from .services import (
    prepare_sale,
    prepare_quotation,
    calculate_sale_total,
    complete_sale,
)



# =====================================================
# SALES DASHBOARD
# =====================================================


@login_required
def sales_dashboard(request):

    today = timezone.now().date()
    today_sales = Sale.objects.filter(
        sale_date=today,
        status="completed"
    ).aggregate(
        total=Sum(
            "total_amount"
        )
    )["total"] or 0



    monthly_sales = Sale.objects.filter(
        sale_date__month=today.month,
        sale_date__year=today.year,
        status="completed"
    ).aggregate(
        total=Sum(
            "total_amount"
        )
    )["total"] or 0



    outstanding = Invoice.objects.filter(
        status__in=[
            "unpaid",
            "partial"
        ]
    ).aggregate(
        total=Sum(
            F("total_amount") - F("amount_paid")
        )
    )["total"] or 0



    top_customers = Customer.objects.annotate(
        sales_total=Sum(
            'sales__total_amount'
        )
    ).order_by(
        '-sales_total'
    )[:5]



    context = {

        "today_sales": today_sales,

        "monthly_sales": monthly_sales,

        "outstanding": outstanding,

        "top_customers": top_customers,

    }


    return render(
        request,
        "sales/dashboard.html",
        context
    )



# =====================================================
# CUSTOMER
# =====================================================


@login_required
def customer_list(request):

    customers = Customer.objects.all().order_by("-id")


    return render(
        request,
        "sales/customer_list.html",
        {
            "customers": customers
        }
    )



@login_required
def customer_create(request):

    form = CustomerForm(
        request.POST or None
    )


    if request.method == "POST":

        if form.is_valid():

            form.save()


            messages.success(
                request,
                "Customer created successfully"
            )


            return redirect(
                "customer_list"
            )


    return render(
        request,
        "sales/customer_form.html",
        {
            "form":form
        }
    )



# =====================================================
# SALE CREATE
# =====================================================


@login_required
@transaction.atomic
def sale_create(request):


    if request.method == "POST":


        sale_form = SaleForm(
            request.POST
        )


        if sale_form.is_valid():


            sale = sale_form.save(
                commit=False
            )


            prepare_sale(
                sale
            )


            sale.save()



            formset = SaleItemFormSet(
                request.POST,
                instance=sale,
                prefix="items"
            )



            if formset.is_valid():

                formset.save()


                calculate_sale_total(
                    sale
                )


                messages.success(
                    request,
                    "Sale created successfully"
                )


                return redirect(
                    "sale_detail",
                    sale.id
                )


    else:


        sale_form = SaleForm()


        formset = SaleItemFormSet(
            prefix="items"
        )



    return render(
        request,
        "sales/sale_form.html",
        {
            "sale_form":sale_form,
            "formset":formset
        }
    )



# =====================================================
# SALE LIST
# =====================================================


@login_required
def sale_list(request):

    sales = Sale.objects.all().order_by(
        "-id"
    )


    return render(
        request,
        "sales/sale_list.html",
        {
            "sales":sales
        }
    )



@login_required
def sale_detail(request,pk):

    sale = get_object_or_404(
        Sale,
        id=pk
    )


    invoice = getattr(
        sale,
        "invoice",
        None
    )


    return render(
        request,
        "sales/sale_detail.html",
        {
            "sale":sale,
            "invoice":invoice
        }
    )

@login_required
def invoice_pdf(request, pk):

    invoice = get_object_or_404(
        Invoice,
        id=pk
    )


    return generate_invoice_pdf(
        invoice
    )



# =====================================================
# COMPLETE SALE
# =====================================================


@login_required
@transaction.atomic
def sale_complete(request,pk):


    sale = get_object_or_404(
        Sale,
        id=pk
    )


    if sale.status == "completed":

        messages.warning(
            request,
            "Sale already completed"
        )

        return redirect(
            "sale_detail",
            sale.id
        )



    try:

        invoice = complete_sale(
            sale,
            request.user
        )


        messages.success(
            request,
            "Sale completed successfully"
        )


        return redirect(
            "invoice_detail",
            invoice.id
        )


    except Exception as e:


        messages.error(
            request,
            str(e)
        )


        return redirect(
            "sale_detail",
            sale.id
        )



# =====================================================
# QUOTATION
# =====================================================


@login_required
def quotation_create(request):

    form = SalesQuotationForm(
        request.POST or None
    )


    if request.method=="POST":


        if form.is_valid():


            quotation=form.save(
                commit=False
            )


            prepare_quotation(
                quotation
            )


            quotation.save()


            messages.success(
                request,
                "Quotation created"
            )


            return redirect(
                "quotation_list"
            )


    return render(
        request,
        "sales/quotation_form.html",
        {
            "form":form
        }
    )



@login_required
def quotation_list(request):

    quotations = SalesQuotation.objects.all()


    return render(
        request,
        "sales/quotation_list.html",
        {
            "quotations":quotations
        }
    )



# =====================================================
# INVOICE
# =====================================================


@login_required
def invoice_list(request):

    invoices = Invoice.objects.all().order_by(
        "-id"
    )


    return render(
        request,
        "sales/invoice_list.html",
        {
            "invoices":invoices
        }
    )



@login_required
def invoice_detail(request,pk):

    invoice = get_object_or_404(
        Invoice,
        id=pk
    )


    return render(
        request,
        "sales/invoice_detail.html",
        {
            "invoice":invoice
        }
    )



# =====================================================
# PAYMENT
# =====================================================


@login_required
@transaction.atomic
def payment_create(request):


    form = CustomerPaymentForm(
        request.POST or None
    )



    if request.method=="POST":


        if form.is_valid():


            payment = form.save()



            invoice = payment.invoice



            invoice.amount_paid += (
                payment.amount
            )



            if invoice.amount_paid >= invoice.total_amount:

                invoice.status="paid"


            elif invoice.amount_paid > 0:

                invoice.status="partial"



            invoice.save()



            messages.success(
                request,
                "Payment recorded successfully"
            )


            return redirect(
                "invoice_detail",
                invoice.id
            )



    return render(
        request,
        "sales/payment_form.html",
        {
            "form":form
        }
    )