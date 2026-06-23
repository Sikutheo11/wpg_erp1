from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Sale,
    Invoice,
    SalesQuotation,
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
# QUOTATION TOTAL CALCULATION
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
        - quotation.discount
        + quotation.tax
    )


    quotation.total_amount = total

    quotation.save(
        update_fields=[
            "total_amount"
        ]
    )


    return total



# =====================================================
# SALE TOTAL CALCULATION
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
        - sale.discount
        + sale.tax
    )


    sale.total_amount = total


    sale.save(
        update_fields=[
            "total_amount"
        ]
    )


    return total



# =====================================================
# STOCK REDUCTION
# =====================================================


def reduce_stock_after_sale(
        sale,
        user=None
):


    for item in sale.items.all():


        product = item.product


        # Check available stock

        if product.current_stock < item.quantity:

            raise Exception(
                f"Not enough stock for {product.name}"
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


def create_invoice_from_sale(sale):


    invoice = Invoice.objects.create(

        sale=sale,

        invoice_no=
            generate_invoice_number(),

        invoice_date=
            timezone.now().date(),

        due_date=
            timezone.now().date(),

        total_amount=
            sale.total_amount

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


    # calculate total

    calculate_sale_total(
        sale
    )


    # reduce stock

    reduce_stock_after_sale(
        sale,
        user
    )


    # change status

    sale.status = "completed"

    sale.save(
        update_fields=[
            "status"
        ]
    )


    # create invoice

    invoice = create_invoice_from_sale(
        sale
    )


    return invoice



# =====================================================
# CREATE SALE NUMBER
# =====================================================


def prepare_sale(sale):

    if not sale.sale_no:

        sale.sale_no = (
            generate_sale_number()
        )


    sale.save()


    return sale



# =====================================================
# CREATE QUOTATION NUMBER
# =====================================================


def prepare_quotation(quotation):

    if not quotation.quotation_no:

        quotation.quotation_no = (
            generate_quotation_number()
        )


    quotation.save()


    return quotation