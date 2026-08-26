from datetime import date
from core.workflow_service import WorkflowService
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from core.permissions import wpg_permission_required
from inventory.models import Product
from orders.models import Order
from .dashboard import get_sales_dashboard
from .models import (
    Customer,
    CustomerPayment,
    Invoice,
    Sale,
    SalesQuotation,
    SalesQuotationItem,
    EnterpriseInvoice,
)
from .services import (
    CustomerService,
    QuotationConversionService,
    QuotationService,
)

from .forms import (
    SalesQuotationForm,
    SalesQuotationItemFormSet,
    EnterpriseInvoiceDraftForm,
)
from .pdf import enterprise_invoice_pdf_response
from .services.invoice_service import EnterpriseInvoiceService
from .services.invoice_delivery_service import InvoiceDeliveryService


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
@wpg_permission_required("sales.view_sale", feature_code="SALES_DASHBOARD")
def sales_dashboard(request):
    return render(
        request,
        "sales/dashboard.html",
        get_sales_dashboard(request.user),
    )


@login_required
@wpg_permission_required("sales.view_customer", feature_code="CUSTOMER_LIST")
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
@wpg_permission_required("sales.view_customer", feature_code="CUSTOMER_LIST")
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
@wpg_permission_required("sales.add_customer", feature_code="CUSTOMER_LIST", action="add")
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
@wpg_permission_required("sales.change_customer", feature_code="CUSTOMER_LIST", action="change")
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
@wpg_permission_required("sales.delete_customer", feature_code="CUSTOMER_LIST", action="delete")
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
@wpg_permission_required("sales.change_customer", feature_code="CUSTOMER_LIST", action="change")
@require_POST
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
@wpg_permission_required("sales.view_salesquotation", feature_code="QUOTATION_LIST")
def quotation_list(request):
    base_queryset = SalesQuotation.objects.exclude(
        order_type="ECOMMERCE",
    ).select_related(
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
@wpg_permission_required("sales.view_salesquotation", feature_code="QUOTATION_LIST")
def quotation_detail(request, pk):
    quotation = get_object_or_404(
        SalesQuotation.objects.select_related(
            "customer",
            "prepared_by",
            "approved_by",
            "converted_order",
        ).prefetch_related(
            "items__product",
        ),
        pk=pk,
    )
    workflow_actions = (
        WorkflowService.get_available_action_map(
            obj=quotation,
            workflow_code="SALES_QUOTATION",
            user=request.user,
        )
    )

    can_edit_items = (
        quotation.status
        in QuotationService.EDITABLE_STATUSES
        and not quotation.converted_order_id
    )

    can_submit = (
        "sent" in workflow_actions
        and quotation.items.exists()
    )

    can_approve = (
        "approved" in workflow_actions
    )

    can_reject = (
        "rejected" in workflow_actions
    )

    can_cancel = (
        "cancelled" in workflow_actions
    )

    can_convert = (
        "converted" in workflow_actions
        and not quotation.converted_order_id
    )

    return render(
        request,
        "sales/quotations/quotation_detail.html",
        {
            "quotation": quotation,
            "items": quotation.items.all(),

            # Workflow
            "workflow_actions": workflow_actions,
            "workflow_history": (
                WorkflowService.history(
                    quotation
                )
            ),

            # Template compatibility
            "can_edit": can_edit_items,
            "can_submit": can_submit,
            "can_approve": can_approve,
            "can_reject": can_reject,
            "can_cancel": can_cancel,
            "can_convert": can_convert,
        },
    )


@login_required
def customer_quotation_detail(request, pk):
    quotation = get_object_or_404(
        SalesQuotation.objects.select_related("customer", "source_order_request").prefetch_related("items"),
        Q(customer__user=request.user) | Q(source_order_request__user=request.user),
        pk=pk,
    )
    return render(
        request,
        "sales/quotations/customer_quotation_detail.html",
        {"quotation": quotation, "items": quotation.items.all()},
    )


@login_required
@require_POST
def customer_quotation_accept(request, pk):
    quotation = get_object_or_404(
        SalesQuotation,
        Q(customer__user=request.user) | Q(source_order_request__user=request.user),
        pk=pk,
    )
    try:
        QuotationService.approve(
            quotation=quotation,
            approved_by=request.user,
            actor=request.user,
        )
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    else:
        messages.success(request, "Quotation accepted. Your order is now ready for production.")
    return redirect("sales:customer_quotation_detail", pk=quotation.pk)


@login_required
@require_POST
def customer_quotation_revision(request, pk):
    quotation = get_object_or_404(
        SalesQuotation,
        Q(customer__user=request.user) | Q(source_order_request__user=request.user),
        pk=pk,
    )
    try:
        QuotationService.reject(
            quotation=quotation,
            reason=request.POST.get("reason", ""),
            actor=request.user,
        )
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    else:
        messages.warning(request, "Your revision request was sent to the team.")
    return redirect("sales:customer_quotation_detail", pk=quotation.pk)

@login_required
@wpg_permission_required("sales.add_salesquotation", feature_code="QUOTATION_LIST", action="add")
def quotation_create(request):
    quotation = SalesQuotation()

    published_products = (
        Product.objects
        .filter(is_published=True)
        .order_by("name")
    )

    # Product information used by JavaScript.
    # Keys are strings because selected option values come from HTML.
    product_lookup = {
        str(product.pk): {
            "id": product.pk,
            "name": product.name,
            "selling_price": str(
                product.selling_price or 0
            ),
            "business_unit": (
                product.business_unit or ""
            ),
        }
        for product in published_products
    }

    if request.method == "POST":
        form = SalesQuotationForm(
            request.POST,
            instance=quotation,
        )

        formset = SalesQuotationItemFormSet(
            request.POST,
            instance=quotation,
        )

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    header = form.cleaned_data

                    quotation = (
                        QuotationService
                        .create_quotation(
                            customer=header["customer"],
                            business_unit=header[
                                "business_unit"
                            ],
                            order_type=header[
                                "order_type"
                            ],
                            quotation_date=header.get(
                                "quotation_date"
                            ),
                            valid_until=header.get(
                                "valid_until"
                            ),
                            discount=header.get(
                                "discount",
                                0,
                            ),
                            tax=header.get(
                                "tax",
                                0,
                            ),
                            notes=header.get(
                                "notes",
                                "",
                            ),
                            prepared_by=request.user,
                            actor=request.user,
                        )
                    )

                    formset.instance = quotation

                    items = formset.save(
                        commit=False
                    )

                    for item in items:
                        item.quotation = quotation

                        # Keep a name snapshot even when
                        # an inventory product was selected.
                        if (
                            item.product
                            and not item.product_name
                        ):
                            item.product_name = (
                                item.product.name
                            )

                        item.full_clean()
                        item.save()

                    for deleted_item in (
                        formset.deleted_objects
                    ):
                        if deleted_item.pk:
                            deleted_item.delete()

                    QuotationService.recalculate_totals(
                        quotation
                    )

            except ValidationError as error:
                messages.error(
                    request,
                    _validation_message(error),
                )

            except Exception as error:
                messages.error(
                    request,
                    (
                        "Quotation could not be created: "
                        f"{error}"
                    ),
                )

            else:
                messages.success(
                    request,
                    (
                        f"Quotation "
                        f"{quotation.quotation_no} "
                        "created successfully."
                    ),
                )

                return redirect(
                    "sales:quotation_detail",
                    pk=quotation.pk,
                )

    else:
        form = SalesQuotationForm(
            instance=quotation,
        )

        formset = SalesQuotationItemFormSet(
            instance=quotation,
        )

    return render(
        request,
        "sales/quotations/quotation_form.html",
        {
            "page_title": (
                "Create Sales Quotation"
            ),
            "quotation": quotation,
            "form": form,
            "formset": formset,
            "product_lookup": product_lookup,
        },
    )


@login_required
@require_POST
@wpg_permission_required("sales.add_salesquotation", feature_code="QUOTATION_LIST", action="add")
def quotation_create_from_order(request, order_pk):
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), pk=order_pk)
    try:
        quotation = QuotationService.create_from_order(order=order, actor=request.user)
    except ValidationError as error:
        messages.error(request, _validation_message(error))
        return redirect("orders:order_detail", pk=order.pk)
    messages.success(request, "Customer quotation draft created. Add prices and send it to the customer.")
    return redirect("sales:quotation_detail", pk=quotation.pk)

@login_required
@wpg_permission_required("sales.change_salesquotation", feature_code="QUOTATION_LIST", action="change")
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
@wpg_permission_required("sales.change_salesquotation", feature_code="QUOTATION_LIST", action="change")
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
@wpg_permission_required("sales.change_salesquotation", feature_code="QUOTATION_LIST", action="change")
@require_POST
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
@wpg_permission_required("sales.change_salesquotation", feature_code="QUOTATION_LIST", action="change")
@require_POST
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
@wpg_permission_required("sales.approve_salesquotation", feature_code="QUOTATION_APPROVAL", action="approve")
@require_POST
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
@wpg_permission_required("sales.approve_salesquotation", feature_code="QUOTATION_APPROVAL", action="approve")
@require_POST
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
@wpg_permission_required("sales.change_salesquotation", feature_code="QUOTATION_LIST", action="change")
@require_POST
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
@wpg_permission_required("sales.convert_salesquotation", feature_code="QUOTATION_APPROVAL", action="approve")
@require_POST
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
@wpg_permission_required("sales.view_sale", feature_code="SALES_LIST")
def sale_list(request):
    sales = Sale.objects.select_related(
        "customer",
        "warehouse",
        "quotation",
    ).order_by("-created_at")

    return render(
        request,
        "sales/sale_list.html",
        {"sales": sales, "legacy_mode": True},
    )


@login_required
@wpg_permission_required("sales.view_sale", feature_code="SALES_LIST")
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
        "sales/sale_detail.html",
        {"sale": sale, "legacy_mode": True},
    )


@login_required
@wpg_permission_required("sales.change_sale", feature_code="SALES_LIST", action="change")
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
@wpg_permission_required("sales.view_invoice", feature_code="SALES_INVOICES")
def invoice_list(request):
    invoices = EnterpriseInvoice.objects.select_related(
        "order", "customer", "receivable",
    ).order_by("-invoice_date", "-pk")
    invoiceable_orders = Order.objects.filter(
        status__in=EnterpriseInvoiceService.INVOICEABLE_ORDER_STATUSES,
        sales_invoice__isnull=True,
        total_amount__gt=0,
    ).order_by("-created_at")[:50]

    return render(
        request,
        "sales/invoice_list.html",
        {
            "invoices": invoices,
            "invoiceable_orders": invoiceable_orders,
            "legacy_mode": False,
        },
    )


@login_required
@wpg_permission_required("sales.view_invoice", feature_code="SALES_INVOICES")
def invoice_detail(request, pk):
    invoice = (
        EnterpriseInvoice.objects.select_related(
            "order", "customer", "receivable", "issued_by",
        ).prefetch_related("order__items", "deliveries")
        .filter(pk=pk)
        .first()
    )
    if invoice is None:
        legacy_invoice = get_object_or_404(
            Invoice.objects.select_related(
                "sale", "sale__customer",
            ).prefetch_related("payments"),
            pk=pk,
        )
        return render(
            request,
            "sales/invoice_legacy_detail.html",
            {"invoice": legacy_invoice, "legacy_mode": True},
        )
    EnterpriseInvoiceService.sync_payment_status(invoice)

    return render(
        request,
        "sales/invoice_detail.html",
        {"invoice": invoice, "legacy_mode": False},
    )


@login_required
@wpg_permission_required("sales.add_enterpriseinvoice", feature_code="SALES_INVOICES", action="add")
def enterprise_invoice_create(request, order_pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=order_pk)
    if request.method == "POST":
        form = EnterpriseInvoiceDraftForm(request.POST)
        if form.is_valid():
            try:
                invoice = EnterpriseInvoiceService.create_draft(
                    order=order, due_date=form.cleaned_data["due_date"]
                )
                messages.success(request, "Invoice draft created.")
                return redirect("sales:invoice_detail", pk=invoice.pk)
            except ValidationError as error:
                form.add_error(None, _validation_message(error))
    else:
        form = EnterpriseInvoiceDraftForm()
    return render(request, "sales/invoices/invoice_form.html", {"form": form, "order": order})


@login_required
@require_POST
@wpg_permission_required("sales.issue_enterpriseinvoice", feature_code="SALES_INVOICES", action="change")
def enterprise_invoice_issue(request, pk):
    invoice = get_object_or_404(EnterpriseInvoice, pk=pk)
    try:
        EnterpriseInvoiceService.issue(invoice=invoice, actor=request.user)
        messages.success(request, "Invoice issued and Finance receivable created.")
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    return redirect("sales:invoice_detail", pk=pk)


@login_required
@wpg_permission_required("sales.view_enterpriseinvoice", feature_code="SALES_INVOICES")
def enterprise_invoice_pdf(request, pk):
    invoice = get_object_or_404(
        EnterpriseInvoice.objects.select_related("customer", "order").prefetch_related("order__items"), pk=pk
    )
    return enterprise_invoice_pdf_response(invoice, inline=True)


def enterprise_invoice_public_pdf(request, token):
    invoice = get_object_or_404(
        EnterpriseInvoice.objects.select_related("customer", "order").prefetch_related("order__items"),
        public_token=token, status__in=[EnterpriseInvoice.ISSUED, EnterpriseInvoice.PARTIAL, EnterpriseInvoice.PAID],
    )
    return enterprise_invoice_pdf_response(invoice, inline=True)


@login_required
@require_POST
@wpg_permission_required("sales.send_enterpriseinvoice", feature_code="SALES_INVOICES", action="change")
def enterprise_invoice_send(request, pk, channel):
    invoice = get_object_or_404(
        EnterpriseInvoice.objects.select_related("customer", "order", "receivable"), pk=pk
    )
    if invoice.status == EnterpriseInvoice.DRAFT:
        messages.error(request, "Issue the invoice before sending it.")
        return redirect("sales:invoice_detail", pk=pk)
    try:
        if channel == "email":
            InvoiceDeliveryService.send_email(invoice=invoice, actor=request.user, request=request)
        elif channel == "whatsapp":
            InvoiceDeliveryService.send_whatsapp(invoice=invoice, actor=request.user, request=request)
        else:
            raise ValidationError("Unknown delivery channel.")
        messages.success(request, f"Invoice sent by {channel.title()}.")
    except Exception as error:
        messages.error(request, f"Invoice was not sent: {_validation_message(error)}")
    return redirect("sales:invoice_detail", pk=pk)


@login_required
@wpg_permission_required("sales.view_customerpayment", feature_code="SALES_PAYMENTS")
def payment_list(request):
    payments = CustomerPayment.objects.select_related(
        "invoice",
        "invoice__sale",
        "invoice__sale__customer",
    ).order_by("-payment_date", "-pk")

    return render(
        request,
        "sales/payment_list.html",
        {"payments": payments, "legacy_mode": True},
    )


@login_required
@wpg_permission_required("sales.view_sale", feature_code="SALES_REPORTS")
def sales_report(request):
    return render(
        request,
        "sales/sales_report.html",
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
