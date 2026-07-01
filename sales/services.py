# sales/services.py

from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone

from .models import (
    Customer,
    SalesQuotation,
    Sale,
    Invoice,
    CustomerPayment,
)

from inventory.models import StockMovement



# =====================================================
# NUMBER GENERATORS
# =====================================================


def generate_quotation_number():

    year = timezone.now().year

    count = SalesQuotation.objects.filter(
        quotation_no__startswith=f"QUO-{year}"
    ).count()

    return f"QUO-{year}-{count + 1:04d}"



def generate_sale_number():

    year = timezone.now().year

    count = Sale.objects.filter(
        sale_no__startswith=f"SALE-{year}"
    ).count()

    return f"SALE-{year}-{count + 1:04d}"



def generate_invoice_number():

    year = timezone.now().year

    count = Invoice.objects.filter(
        invoice_no__startswith=f"INV-{year}"
    ).count()

    return f"INV-{year}-{count + 1:04d}"



# =====================================================
# CUSTOMER SUMMARY
# =====================================================


def get_customer_summary():

    return {

        "total_customers":
            Customer.objects.count(),

    }



# =====================================================
# QUOTATION CALCULATION
# =====================================================


def calculate_quotation_total(quotation):

    subtotal = Decimal("0")


    for item in quotation.items.all():

        subtotal += (
            item.quantity *
            item.unit_price
        )


    total = (
        subtotal
        -
        quotation.discount
        +
        quotation.tax
    )


    quotation.total_amount = total


    quotation.save(
        update_fields=[
            "total_amount"
        ]
    )


    return total



# =====================================================
# SALE CALCULATION
# =====================================================


def calculate_sale_total(sale):

    subtotal = Decimal("0")


    for item in sale.items.all():

        subtotal += (
            item.quantity *
            item.unit_price
        )


    total = (
        subtotal
        -
        sale.discount
        +
        sale.tax
    )


    sale.total_amount = total


    sale.save(
        update_fields=[
            "total_amount"
        ]
    )


    return total



# =====================================================
# INVENTORY STOCK REDUCTION
# =====================================================


def reduce_stock_after_sale(
        sale,
        user=None
):


    for item in sale.items.all():


        product = item.product


        if product.current_stock < item.quantity:

            raise Exception(
                f"Not enough stock for {product}"
            )


        StockMovement.objects.create(

            product=product,

            movement_type="OUT",

            quantity=item.quantity,

            unit_cost=product.selling_price,

            reference_no=sale.sale_no,

            warehouse=sale.warehouse,

            created_by=user

        )



# =====================================================
# CREATE INVOICE
# =====================================================


def create_invoice_from_sale(
        sale
):


    invoice = Invoice.objects.create(

        sale=sale,

        invoice_no=
            generate_invoice_number(),

        invoice_date=
            timezone.now().date(),

        due_date=
            timezone.now().date()
            +
            timedelta(days=30),

        total_amount=
            sale.total_amount,

        amount_paid=0,

        status="pending"

    )


    return invoice



# =====================================================
# COMPLETE SALE PROCESS
# =====================================================


@transaction.atomic
def complete_sale(
        sale,
        user=None
):


    # Calculate total

    calculate_sale_total(
        sale
    )


    # Reduce inventory

    reduce_stock_after_sale(
        sale,
        user
    )


    # Update sale status

    sale.status = "completed"


    sale.save(
        update_fields=[
            "status"
        ]
    )


    # Create invoice

    invoice = create_invoice_from_sale(
        sale
    )


    return invoice



# =====================================================
# PREPARE DOCUMENT NUMBERS
# =====================================================


def prepare_sale(sale):

    if not sale.sale_no:

        sale.sale_no = (
            generate_sale_number()
        )


    sale.save()

    return sale



def prepare_quotation(
        quotation
):

    if not quotation.quotation_no:

        quotation.quotation_no = (
            generate_quotation_number()
        )


    quotation.save()

    return quotation



# =====================================================
# SALES DASHBOARD SUMMARY
# =====================================================


def get_sales_summary():

    total_sales_amount = (
        Sale.objects.aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0")
    )


    total_invoice_amount = (
        Invoice.objects.aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0")
    )


    total_paid_amount = (
        Invoice.objects.aggregate(
            total=Sum(
                "amount_paid"
            )
        )["total"]
        or Decimal("0")
    )


    return {


        "total_customers":
            Customer.objects.count(),


        "total_quotations":
            SalesQuotation.objects.count(),


        "total_sales":
            Sale.objects.count(),


        "total_sales_amount":
            total_sales_amount,


        "total_invoices":
            Invoice.objects.count(),


        "total_invoice_amount":
            total_invoice_amount,


        "total_paid_amount":
            total_paid_amount,


        "outstanding_amount":
            total_invoice_amount
            -
            total_paid_amount,


        "recent_sales":
            Sale.objects
            .select_related(
                "customer"
            )
            .order_by(
                "-created_at"
            )[:10]

    }