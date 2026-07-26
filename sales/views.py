from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import Product

from .dashboard import get_sales_dashboard
from .models import (
    Customer,
    CustomerPayment,
    Invoice,
    Sale,
    SalesQuotation,
    SalesQuotationItem,
)
from .services import (
    CustomerService,
    QuotationConversionService,
    QuotationService,
)


def _validation_message(error):
    if hasattr(error, "messages"):
        return "; ".join(error.messages)
    return str(error)


def _parse_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@login_required
def sales_dashboard(request):
    return render(
        request,
        "sales/dashboard.html",
        get_sales_dashboard(request.user),
    )


@login_required
def customer_list(request):
    search = request.GET.get("q", "").strip()
    customer_type = request.GET.get(
        "customer_type",
        "",
    ).strip().upper()
    active_filter = request.GET.get(
        "active",
        "active",
    ).strip().lower()

    customers = CustomerService.search_customers(
        query=search,
        active_only=(active_filter != "all"),
        customer_type=customer_type or None,
    )

    return render(
        request,
        "sales/customers/customer_list.html",
        {
            "customers": customers,
            "search": search,
            "selected_customer_type": customer_type,
            "selected_active_filter": active_filter,
            "customer_type_choices": Customer.CUSTOMER_TYPES,
        },
    )


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(
        Customer.objects.select_related("user"),
        pk=pk,
    )

    return render(
        request,
        "sales/customers/customer_detail.html",
        {
            "customer": customer,
            "quotations": customer.quotations.all().order_by("-created_at"),
        },
    )


@login_required
def customer_create(request):
    if request.method == "POST":
        try:
            customer = CustomerService.create_customer(
                customer_type=request.POST.get(
                    "customer_type",
                    "INDIVIDUAL",
                ),
                full_name=request.POST.get("full_name", ""),
                company_name=request.POST.get("company_name", ""),
                phone=request.POST.get("phone", ""),
                email=request.POST.get("email", ""),
                address=request.POST.get("address", ""),
                tax_number=request.POST.get("tax_number", ""),
                credit_limit=request.POST.get("credit_limit", 0),
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(
                request,
                f"Customer {customer.display_name} created successfully.",
            )
            return redirect("sales:customer_detail", pk=customer.pk)

    return render(
        request,
        "sales/customers/customer_form.html",
        {
            "customer": None,
            "customer_type_choices": Customer.CUSTOMER_TYPES,
            "page_title": "Create Customer",
        },
    )


@login_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        try:
            customer = CustomerService.update_customer(
                customer=customer,
                customer_type=request.POST.get(
                    "customer_type",
                    customer.customer_type,
                ),
                full_name=request.POST.get("full_name", customer.full_name),
                company_name=request.POST.get(
                    "company_name",
                    customer.company_name,
                ),
                phone=request.POST.get("phone", customer.phone),
                email=request.POST.get("email", customer.email),
                address=request.POST.get("address", customer.address),
                tax_number=request.POST.get(
                    "tax_number",
                    customer.tax_number,
                ),
                credit_limit=request.POST.get(
                    "credit_limit",
                    customer.credit_limit,
                ),
                is_active=(request.POST.get("is_active") == "on"),
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Customer updated successfully.")
            return redirect("sales:customer_detail", pk=customer.pk)

    return render(
        request,
        "sales/customers/customer_form.html",
        {
            "customer": customer,
            "customer_type_choices": Customer.CUSTOMER_TYPES,
            "page_title": "Update Customer",
        },
    )


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        try:
            CustomerService.deactivate_customer(
                customer=customer,
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Customer deactivated successfully.")
            return redirect("sales:customer_list")

    return render(
        request,
        "sales/customers/customer_delete.html",
        {"customer": customer},
    )


@login_required
def customer_activate(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        try:
            CustomerService.activate_customer(
                customer=customer,
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Customer activated successfully.")

    return redirect("sales:customer_detail", pk=customer.pk)


@login_required
def quotation_list(request):
    base_queryset = SalesQuotation.objects.select_related(
        "customer",
        "prepared_by",
        "approved_by",
        "converted_order",
    ).order_by("-created_at")

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip().lower()
    business_unit = request.GET.get(
        "business_unit",
        "",
    ).strip().upper()

    quotations = base_queryset

    if search:
        quotations = quotations.filter(
            Q(quotation_no__icontains=search)
            | Q(customer__full_name__icontains=search)
            | Q(customer__company_name__icontains=search)
            | Q(customer__phone__icontains=search)
        )

    valid_statuses = {value for value, _ in SalesQuotation.STATUS}
    if status in valid_statuses:
        quotations = quotations.filter(status=status)

    valid_units = {value for value, _ in SalesQuotation.BUSINESS_UNITS}
    if business_unit in valid_units:
        quotations = quotations.filter(business_unit=business_unit)

    return render(
        request,
        "sales/quotations/quotation_list.html",
        {
            "quotations": quotations,
            "search": search,
            "selected_status": status,
            "selected_business_unit": business_unit,
            "status_choices": SalesQuotation.STATUS,
            "business_unit_choices": SalesQuotation.BUSINESS_UNITS,
            "total_count": base_queryset.count(),
            "draft_count": base_queryset.filter(status="draft").count(),
            "sent_count": base_queryset.filter(status="sent").count(),
            "approved_count": base_queryset.filter(status="approved").count(),
            "converted_count": base_queryset.filter(status="converted").count(),
        },
    )


@login_required
def quotation_detail(request, pk):
    quotation = get_object_or_404(
        SalesQuotation.objects.select_related(
            "customer",
            "prepared_by",
            "approved_by",
            "converted_order",
        ).prefetch_related("items__product"),
        pk=pk,
    )

    return render(
        request,
        "sales/quotations/quotation_detail.html",
        {
            "quotation": quotation,
            "items": quotation.items.all(),
            "can_edit": (
                quotation.status in QuotationService.EDITABLE_STATUSES
                and not quotation.converted_order_id
            ),
            "can_submit": (
                quotation.status in QuotationService.EDITABLE_STATUSES
                and quotation.items.exists()
            ),
            "can_approve": quotation.status == "sent",
            "can_convert": (
                quotation.status == "approved"
                and not quotation.converted_order_id
            ),
        },
    )

@login_required
def quotation_create(request):
    customers = (
        Customer.objects
        .filter(is_active=True)
        .order_by(
            "company_name",
            "full_name",
            "phone",
        )
    )

    context = {
        "quotation": None,
        "customers": customers,
        "business_unit_choices": SalesQuotation.BUSINESS_UNITS,
        "order_type_choices": SalesQuotation.ORDER_TYPES,
    }

    if request.method == "POST":
        customer_id = request.POST.get(
            "customer",
            "",
        ).strip()

        if not customer_id:
            messages.error(
                request,
                "Please select a customer.",
            )
            return render(
                request,
                "sales/quotations/quotation_form.html",
                context,
            )

        customer = (
            Customer.objects
            .filter(
                pk=customer_id,
                is_active=True,
            )
            .first()
        )

        if customer is None:
            messages.error(
                request,
                (
                    "The selected customer does not exist "
                    "or is inactive."
                ),
            )
            return render(
                request,
                "sales/quotations/quotation_form.html",
                context,
            )

        try:
            quotation = QuotationService.create_quotation(
                customer=customer,
                business_unit=request.POST.get(
                    "business_unit",
                    "",
                ),
                order_type=request.POST.get(
                    "order_type",
                    "",
                ),
                quotation_date=_parse_date(
                    request.POST.get(
                        "quotation_date"
                    )
                ),
                valid_until=_parse_date(
                    request.POST.get(
                        "valid_until"
                    )
                ),
                discount=request.POST.get(
                    "discount",
                    0,
                ),
                tax=request.POST.get(
                    "tax",
                    0,
                ),
                notes=request.POST.get(
                    "notes",
                    "",
                ),
                prepared_by=request.user,
                actor=request.user,
            )

        except ValidationError as error:
            messages.error(
                request,
                _validation_message(error),
            )

        else:
            messages.success(
                request,
                (
                    f"Quotation {quotation.quotation_no} "
                    "created successfully."
                ),
            )

            return redirect(
                "sales:quotation_detail",
                pk=quotation.pk,
            )

    return render(
        request,
        "sales/quotations/quotation_form.html",
        context,
    )

@login_required
def quotation_item_create(request, pk):
    quotation = get_object_or_404(
        SalesQuotation,
        pk=pk,
    )

    if request.method == "POST":
        product = None
        product_id = request.POST.get("product")

        if product_id:
            product = get_object_or_404(
                Product,
                pk=product_id,
            )

        try:
            QuotationService.add_item(
                quotation=quotation,
                product=product,
                product_name=request.POST.get("product_name", ""),
                specifications=request.POST.get("specifications", ""),
                quantity=request.POST.get("quantity", 1),
                unit_price=request.POST.get("unit_price") or None,
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Quotation item added successfully.")
            return redirect("sales:quotation_detail", pk=quotation.pk)

    products = Product.objects.filter(
        is_published=True,
    ).order_by("name")

    if quotation.business_unit != "MARKETPLACE":
        products = products.filter(
            business_unit=quotation.business_unit
        )

    return render(
        request,
        "sales/quotations/quotation_item_form.html",
        {
            "quotation": quotation,
            "products": products,
            "item": None,
            "page_title": "Add Quotation Item",
        },
    )


@login_required
def quotation_item_update(request, pk, item_pk):
    quotation = get_object_or_404(
        SalesQuotation,
        pk=pk,
    )

    item = get_object_or_404(
        SalesQuotationItem,
        pk=item_pk,
        quotation=quotation,
    )

    if request.method == "POST":
        product = None
        product_id = request.POST.get("product")

        if product_id:
            product = get_object_or_404(
                Product,
                pk=product_id,
            )

        try:
            QuotationService.update_item(
                item=item,
                product=product,
                product_name=request.POST.get("product_name", ""),
                specifications=request.POST.get("specifications", ""),
                quantity=request.POST.get("quantity"),
                unit_price=request.POST.get("unit_price"),
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Quotation item updated successfully.")
            return redirect("sales:quotation_detail", pk=quotation.pk)

    products = Product.objects.filter(
        is_published=True,
    ).order_by("name")

    if quotation.business_unit != "MARKETPLACE":
        products = products.filter(
            business_unit=quotation.business_unit
        )

    return render(
        request,
        "sales/quotations/quotation_item_form.html",
        {
            "quotation": quotation,
            "products": products,
            "item": item,
            "page_title": "Update Quotation Item",
        },
    )


@login_required
def quotation_item_delete(request, pk, item_pk):
    quotation = get_object_or_404(
        SalesQuotation,
        pk=pk,
    )

    item = get_object_or_404(
        SalesQuotationItem,
        pk=item_pk,
        quotation=quotation,
    )

    if request.method == "POST":
        try:
            QuotationService.remove_item(
                item=item,
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Quotation item removed successfully.")

    return redirect("sales:quotation_detail", pk=quotation.pk)


@login_required
def quotation_submit(request, pk):
    quotation = get_object_or_404(SalesQuotation, pk=pk)

    if request.method == "POST":
        try:
            QuotationService.submit(
                quotation=quotation,
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Quotation submitted successfully.")

    return redirect("sales:quotation_detail", pk=quotation.pk)


@login_required
def quotation_approve(request, pk):
    quotation = get_object_or_404(SalesQuotation, pk=pk)

    if request.method == "POST":
        try:
            QuotationService.approve(
                quotation=quotation,
                approved_by=request.user,
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.success(request, "Quotation approved successfully.")

    return redirect("sales:quotation_detail", pk=quotation.pk)


@login_required
def quotation_reject(request, pk):
    quotation = get_object_or_404(SalesQuotation, pk=pk)

    if request.method == "POST":
        try:
            QuotationService.reject(
                quotation=quotation,
                reason=request.POST.get("reason", ""),
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.warning(request, "Quotation rejected.")

    return redirect("sales:quotation_detail", pk=quotation.pk)


@login_required
def quotation_cancel(request, pk):
    quotation = get_object_or_404(SalesQuotation, pk=pk)

    if request.method == "POST":
        try:
            QuotationService.cancel(
                quotation=quotation,
                reason=request.POST.get("reason", ""),
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, _validation_message(error))
        else:
            messages.warning(request, "Quotation cancelled.")

    return redirect("sales:quotation_detail", pk=quotation.pk)


@login_required
def quotation_convert(request, pk):
    quotation = get_object_or_404(
        SalesQuotation,
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "sales:quotation_detail",
            pk=quotation.pk,
        )

    try:
        result = QuotationConversionService.convert_to_order(
            quotation=quotation,
            actor=request.user,
        )
    except ValidationError as error:
        messages.error(request, _validation_message(error))
        return redirect(
            "sales:quotation_detail",
            pk=quotation.pk,
        )

    order = result["order"]

    messages.success(
        request,
        (
            f"Quotation {quotation.quotation_no} converted "
            f"to order {order.order_number}."
        ),
    )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )


@login_required
def sale_list(request):
    sales = Sale.objects.select_related(
        "customer",
        "warehouse",
        "quotation",
    ).order_by("-created_at")

    return render(
        request,
        "sales/sales/sale_list.html",
        {"sales": sales, "legacy_mode": True},
    )


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related(
            "customer",
            "warehouse",
            "quotation",
        ).prefetch_related("items__product"),
        pk=pk,
    )

    return render(
        request,
        "sales/sales/sale_detail.html",
        {"sale": sale, "legacy_mode": True},
    )


@login_required
def complete_sale_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)

    messages.warning(
        request,
        (
            "Legacy sales cannot be completed through the old workflow. "
            "Convert an approved quotation into an Enterprise Order."
        ),
    )

    return redirect("sales:sale_detail", pk=sale.pk)


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related(
        "sale",
        "sale__customer",
    ).order_by("-invoice_date", "-pk")

    return render(
        request,
        "sales/invoices/invoice_list.html",
        {"invoices": invoices, "legacy_mode": True},
    )


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "sale",
            "sale__customer",
        ).prefetch_related("payments"),
        pk=pk,
    )

    return render(
        request,
        "sales/invoices/invoice_detail.html",
        {"invoice": invoice, "legacy_mode": True},
    )


@login_required
def payment_list(request):
    payments = CustomerPayment.objects.select_related(
        "invoice",
        "invoice__sale",
        "invoice__sale__customer",
    ).order_by("-payment_date", "-pk")

    return render(
        request,
        "sales/payments/payment_list.html",
        {"payments": payments, "legacy_mode": True},
    )


@login_required
def sales_report(request):
    return render(
        request,
        "sales/reports/sales_report.html",
        {
            "sales": Sale.objects.select_related(
                "customer",
                "quotation",
            ).order_by("-sale_date", "-pk"),
            "quotations": SalesQuotation.objects.select_related(
                "customer",
                "converted_order",
            ).order_by("-created_at"),
        },
    )
