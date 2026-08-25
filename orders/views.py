from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_POST
from core.permissions import PermissionService, wpg_permission_required
from .models import Order
from .services.delivery_service import DeliveryService
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from .forms import (
    OrderForm,
    OrderItemForm,
)
from .models import (
    Order,
    OrderItem,
)
from inventory.models import StockReservation
from .services.inventory_fulfilment_service import (
    InventoryFulfilmentService,
)
from orders.services import DeliveryService
from .services import (
    OrderService,
    OrderItemService,
    OrderRoutingService,
    OrderFulfilmentService,
    DeliveryService,
)


# =========================================================
# BUSINESS UNIT CONFIGURATION
# =========================================================

BUSINESS_UNITS_CONFIG = [
    {
        "code": "FURNITURE",
        "name": "Furniture & Manufacturing",
        "description": (
            "Furniture sales, custom furniture, "
            "restocking and product development."
        ),
        "icon": "bi bi-hammer",
    },
    {
        "code": "CONSTRUCTION",
        "name": "Construction",
        "description": (
            "Construction projects, renovation, "
            "installation and contract services."
        ),
        "icon": "bi bi-building",
    },
    {
        "code": "AGRICULTURE",
        "name": "Agriculture / Poultry",
        "description": (
            "Eggs, chicks, chickens, feed, manure "
            "and other poultry products."
        ),
        "icon": "bi bi-egg",
    },
    {
        "code": "MARKETPLACE",
        "name": "Marketplace",
        "description": (
            "Online orders for products from "
            "different WPG business units."
        ),
        "icon": "bi bi-shop",
    },
]


# =========================================================
# ORDER TYPES BY BUSINESS UNIT
# =========================================================

ORDER_TYPES_BY_UNIT = {
    "FURNITURE": [
        {
            "code": "ECOMMERCE",
            "name": "Ecommerce Order",
            "description": "Online furniture order.",
            "icon": "bi bi-cart",
        },
        {
            "code": "CUSTOM_FURNITURE",
            "name": "Custom Furniture Order",
            "description": (
                "Furniture made according to "
                "customer specifications."
            ),
            "icon": "bi bi-rulers",
        },
        {
            "code": "RESTOCK",
            "name": "Restock Existing Product",
            "description": (
                "Produce furniture to replenish stock."
            ),
            "icon": "bi bi-box-seam",
        },
        {
            "code": "NEW_PRODUCT",
            "name": "New Product Development",
            "description": (
                "Develop or prototype a new product."
            ),
            "icon": "bi bi-lightbulb",
        },
        {
            "code": "POS",
            "name": "Point of Sale",
            "description": (
                "Direct sale from showroom or shop."
            ),
            "icon": "bi bi-shop-window",
        },
    ],

    "CONSTRUCTION": [
        {
            "code": "PROJECT",
            "name": "Construction Project",
            "description": (
                "New building or construction contract."
            ),
            "icon": "bi bi-building",
        },
        {
            "code": "CUSTOM_ORDER",
            "name": "Custom Construction Order",
            "description": (
                "Customer-specific construction work."
            ),
            "icon": "bi bi-tools",
        },
        {
            "code": "MAINTENANCE",
            "name": "Renovation / Maintenance",
            "description": (
                "Repair, renovation or maintenance work."
            ),
            "icon": "bi bi-wrench-adjustable",
        },
    ],

    "AGRICULTURE": [
        {
            "code": "ECOMMERCE",
            "name": "Ecommerce Order",
            "description": (
                "Online order for poultry products."
            ),
            "icon": "bi bi-cart",
        },
        {
            "code": "RESTOCK",
            "name": "Restock Order",
            "description": (
                "Produce or acquire poultry products "
                "to replenish stock."
            ),
            "icon": "bi bi-box-seam",
        },
        {
            "code": "CUSTOM_ORDER",
            "name": "Customer Supply Order",
            "description": (
                "Special supply request from a customer."
            ),
            "icon": "bi bi-clipboard-check",
        },
        {
            "code": "POS",
            "name": "Point of Sale",
            "description": (
                "Direct poultry product sale."
            ),
            "icon": "bi bi-shop",
        },
    ],

    "MARKETPLACE": [
        {
            "code": "ECOMMERCE",
            "name": "Marketplace Order",
            "description": (
                "Online order routed to the owning "
                "business unit."
            ),
            "icon": "bi bi-bag",
        },
    ],
}


def _order_type_url(business_unit):
    """
    Build the order type selection URL with its query parameter.
    """

    base_url = reverse(
        "orders:order_type_select"
    )

    query_string = urlencode(
        {
            "business_unit": business_unit,
        }
    )

    return f"{base_url}?{query_string}"


def _validation_message(error):
    """
    Convert Django ValidationError into one readable message.
    """

    if hasattr(error, "messages"):
        return "; ".join(error.messages)

    return str(error)


# =========================================================
# SELECT BUSINESS UNIT
# =========================================================

@login_required
@wpg_permission_required("orders.add_order", feature_code="ORDER_LIST", action="add")
def business_unit_select(request):
    return render(
        request,
        "orders/business_unit_select.html",
        {
            "business_units": BUSINESS_UNITS_CONFIG,
        },
    )


# =========================================================
# SELECT ORDER TYPE
# =========================================================

@login_required
@wpg_permission_required("orders.add_order", feature_code="ORDER_LIST", action="add")
def order_type_select(request):
    business_unit = request.GET.get(
        "business_unit",
        "",
    ).strip().upper()

    valid_business_units = {
        value
        for value, label in Order.BUSINESS_UNITS
    }

    if business_unit not in valid_business_units:
        messages.info(
            request,
            "Select a valid business unit first.",
        )

        return redirect(
            "orders:business_unit_select"
        )

    order_types = ORDER_TYPES_BY_UNIT.get(
        business_unit,
        [],
    )

    if not order_types:
        messages.warning(
            request,
            (
                "No order types are configured "
                "for the selected business unit."
            ),
        )

        return redirect(
            "orders:business_unit_select"
        )

    return render(
        request,
        "orders/order_type_select.html",
        {
            "business_unit": business_unit,
            "business_unit_display": dict(
                Order.BUSINESS_UNITS
            ).get(
                business_unit,
                business_unit,
            ),
            "order_types": order_types,
        },
    )


# =========================================================
# CREATE ORDER
# =========================================================

@login_required
@wpg_permission_required("orders.add_order", feature_code="ORDER_LIST", action="add")
def order_create(request):
    business_unit = (
        request.GET.get("business_unit")
        or request.POST.get("business_unit")
        or ""
    ).strip().upper()

    order_type = (
        request.GET.get("type")
        or request.POST.get("order_type")
        or ""
    ).strip().upper()

    valid_business_units = {
        value
        for value, label in Order.BUSINESS_UNITS
    }

    valid_model_order_types = {
        value
        for value, label in Order.ORDER_TYPES
    }

    if business_unit not in valid_business_units:
        messages.info(
            request,
            "Select a valid business unit first.",
        )

        return redirect(
            "orders:business_unit_select"
        )

    configured_types = {
        item["code"]
        for item in ORDER_TYPES_BY_UNIT.get(
            business_unit,
            [],
        )
    }

    if order_type not in configured_types:
        messages.info(
            request,
            (
                "Select an order type that belongs "
                "to the selected business unit."
            ),
        )

        return redirect(
            _order_type_url(
                business_unit
            )
        )

    if order_type not in valid_model_order_types:
        messages.error(
            request,
            (
                f"The order type '{order_type}' is not yet "
                "registered in Order.ORDER_TYPES."
            ),
        )

        return redirect(
            _order_type_url(
                business_unit
            )
        )

    if request.method == "POST":
        form = OrderForm(
            request.POST,
            order_type=order_type,
            business_unit=business_unit,
        )
        item_form = OrderItemForm(
            request.POST,
            request.FILES,
            order_type=order_type,
            business_unit=business_unit,
        )

        if form.is_valid() and item_form.is_valid():
            data = form.cleaned_data
            item_data = item_form.cleaned_data

            try:
                with transaction.atomic():
                    order = OrderService.create_order(
                        user=request.user,
                        business_unit=business_unit,
                        order_type=order_type,
                        customer_name=data.get("customer_name", ""),
                        customer_phone=data.get("customer_phone", ""),
                        customer_email=data.get("customer_email", ""),
                        province=data.get("province", ""),
                        district=data.get("district", ""),
                        sector=data.get("sector", ""),
                        cell=data.get("cell", ""),
                        village=data.get("village", ""),
                        delivery_address=data.get("delivery_address", ""),
                        notes=data.get("notes", ""),
                        discount=data.get("discount", 0),
                        tax=data.get("tax", 0),
                        expected_delivery_date=data.get("expected_delivery_date"),
                    )
                    OrderItemService.add_item(
                        order=order,
                        product=item_data.get("product"),
                        product_name=item_data.get("product_name", ""),
                        quantity=item_data.get("quantity"),
                        specifications=item_data.get("specifications", ""),
                        price=item_data.get("price"),
                        reference_image=item_data.get("reference_image"),
                        design_attachment=item_data.get("design_attachment"),
                        length_cm=item_data.get("length_cm"),
                        width_cm=item_data.get("width_cm"),
                        height_cm=item_data.get("height_cm"),
                        material_preference=item_data.get("material_preference", ""),
                        colour=item_data.get("colour", ""),
                        finish=item_data.get("finish", ""),
                        customer_budget=item_data.get("customer_budget"),
                        actor=request.user,
                    )

            except ValidationError as error:
                form.add_error(
                    None,
                    _validation_message(error),
                )

            else:
                messages.success(
                    request,
                    (
                        f"Order {order.order_number} "
                        "created successfully."
                    ),
                )

                return redirect(
                    "orders:order_detail",
                    pk=order.pk,
                )

    else:
        form = OrderForm(
            order_type=order_type,
            business_unit=business_unit,
        )
        item_form = OrderItemForm(
            order_type=order_type,
            business_unit=business_unit,
        )

    return render(
        request,
        "orders/order_form.html",
        {
            "form": form,
            "item_form": item_form,
            "business_unit": business_unit,
            "order_type": order_type,
            "business_unit_display": dict(
                Order.BUSINESS_UNITS
            ).get(
                business_unit,
                business_unit,
            ),
            "order_type_display": dict(
                Order.ORDER_TYPES
            ).get(
                order_type,
                order_type,
            ),
        },
    )

# =========================================================
# ORDER LIST
# =========================================================

@login_required
@wpg_permission_required("orders.view_order", feature_code="ORDER_LIST")
def order_list(request):
    orders = (
        Order.objects
        .select_related(
            "user",
            "delivered_by",
        )
        .prefetch_related(
            "items",
        )
        .order_by("-created_at")
    )

    search = (
        request.GET.get("q", "")
        .strip()
    )

    status = (
        request.GET.get("status", "")
        .strip()
        .upper()
    )

    business_unit = (
        request.GET.get("business_unit", "")
        .strip()
        .upper()
    )

    order_type = (
        request.GET.get("order_type", "")
        .strip()
        .upper()
    )

    if search:
        orders = orders.filter(
            Q(order_number__icontains=search)
            | Q(customer_name__icontains=search)
            | Q(customer_phone__icontains=search)
            | Q(customer_email__icontains=search)
        )

    valid_statuses = {
        value
        for value, label in Order.STATUS
    }

    if status in valid_statuses:
        orders = orders.filter(
            status=status
        )

    valid_business_units = {
        value
        for value, label in Order.BUSINESS_UNITS
    }

    if business_unit in valid_business_units:
        orders = orders.filter(
            business_unit=business_unit
        )

    valid_order_types = {
        value
        for value, label in Order.ORDER_TYPES
    }

    if order_type in valid_order_types:
        orders = orders.filter(
            order_type=order_type
        )

    summary = {
        "total_orders": orders.count(),
        "draft_orders": orders.filter(
            status="DRAFT"
        ).count(),
        "pending_orders": orders.filter(
            status="PENDING"
        ).count(),
        "confirmed_orders": orders.filter(
            status="CONFIRMED"
        ).count(),
        "in_production_orders": orders.filter(
            status="IN_PRODUCTION"
        ).count(),
        "ready_orders": orders.filter(
            status="READY"
        ).count(),
        "delivered_orders": orders.filter(
            status="DELIVERED"
        ).count(),
    }

    return render(
        request,
        "orders/order_list.html",
        {
            "orders": orders,
            "summary": summary,
            "search": search,
            "selected_status": status,
            "selected_business_unit": business_unit,
            "selected_order_type": order_type,
            "status_choices": Order.STATUS,
            "business_unit_choices": (
                Order.BUSINESS_UNITS
            ),
            "order_type_choices": (
                Order.ORDER_TYPES
            ),
        },
    )


# =========================================================
# ORDER DETAIL

@login_required
@wpg_permission_required("orders.view_order", feature_code="ORDER_LIST")
def order_detail(request, pk):

    order = get_object_or_404(
        Order.objects.select_related(
            "user",
            "delivered_by",
            "production_job",
            "source_sales_quotation",
        ).prefetch_related(
            "items__product",
        ),
        pk=pk,
    )

    items = order.items.all()

    reservations = (
        StockReservation.objects.filter(
            order_item__order=order
        )
        .select_related(
            "product",
            "warehouse",
        )
    )

    fulfilment = None

    if order.status in {
        "PENDING",
        "CONFIRMED",
        "PROCESSING",
        "READY",
        "DELIVERED",
        "COMPLETED",
        "CANCELLED",
    }:
        fulfilment = (
            InventoryFulfilmentService.fulfilment_summary(
                order=order
            )
        )

    item_form = OrderItemForm(
        order_type=order.order_type,
        business_unit=order.business_unit,
    )


    can_edit_items = (
        order.status in {
            "DRAFT",
            "PENDING",
        }
    )

    can_submit = (
        order.status == "DRAFT"
        and items.exists()
    )

    can_confirm = (
        order.status == "PENDING"
    )

    can_process = (
        order.status == "CONFIRMED"
    )

    can_route = (
        order.status == "CONFIRMED"
    )

    can_prepare = (
        order.status == "ROUTED"
    )

    can_mark_ready = (
        order.status in {
            "PROCESSING",
            "IN_PRODUCTION",
        }
    )

    can_dispatch = (
        order.status == "READY"
    )

    can_deliver = (
        order.status in {
            "READY",
            "DISPATCHED",
        }
    )

    can_cancel = (
        order.status not in {
            "DELIVERED",
            "COMPLETED",
            "CANCELLED",
        }
    )

    context = {
        "order": order,
        "items": items,
        "reservations": reservations,
        "fulfilment": fulfilment,
        "item_form": item_form,
        "can_edit_items": can_edit_items,
        "can_submit": can_submit,
        "can_confirm": can_confirm,
        "can_process": can_process,
        "can_route": can_route,
        "can_prepare": can_prepare,
        "can_mark_ready": can_mark_ready,
        "can_dispatch": can_dispatch,
        "can_deliver": can_deliver,
        "can_cancel": can_cancel,
        
    }

    return render(
        request,
        "orders/order_detail.html",
        context,
    )


# =========================================================
# ADD ORDER ITEM
# =========================================================

@login_required
@wpg_permission_required("orders.change_order", feature_code="ORDER_LIST", action="change")
def add_order_item(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if order.status not in {
        "DRAFT",
        "PENDING",
    }:
        messages.error(
            request,
            (
                "Items cannot be added to an order "
                "in its current status."
            ),
        )

        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    form = OrderItemForm(
        request.POST,
        request.FILES,
        order_type=order.order_type,
        business_unit=order.business_unit,
    )

    if form.is_valid():
        data = form.cleaned_data

        try:
            item = OrderItemService.add_item(
                order=order,
                product=data.get("product"),
                product_name=data.get(
                    "product_name",
                    "",
                ),
                quantity=data.get(
                    "quantity"
                ),
                specifications=data.get(
                    "specifications",
                    "",
                ),
                price=data.get("price"),
                reference_image=data.get("reference_image"),
                design_attachment=data.get("design_attachment"),
                length_cm=data.get("length_cm"),
                width_cm=data.get("width_cm"),
                height_cm=data.get("height_cm"),
                material_preference=data.get("material_preference", ""),
                colour=data.get("colour", ""),
                finish=data.get("finish", ""),
                customer_budget=data.get("customer_budget"),
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
                    f"{item.product_name} was added "
                    f"to order {order.order_number}."
                ),
            )

    else:
        error_messages = []

        for errors in form.errors.values():
            for error in errors:
                error_messages.append(
                    str(error)
                )

        messages.error(
            request,
            "; ".join(error_messages),
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

# =========================================================
# EDIT ORDER ITEM
# =========================================================

@login_required
@wpg_permission_required("orders.change_order", feature_code="ORDER_LIST", action="change")
def edit_order_item(request, pk):
    item = get_object_or_404(
        OrderItem.objects.select_related(
            "order",
            "product",
        ),
        pk=pk,
    )

    order = item.order

    if order.status not in {
        "DRAFT",
        "PENDING",
    }:
        messages.error(
            request,
            (
                "Items cannot be edited after "
                "the order has been confirmed."
            ),
        )

        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    if request.method == "POST":
        form = OrderItemForm(
            request.POST,
            request.FILES,
            instance=item,
            order_type=order.order_type,
            business_unit=order.business_unit,
        )

        if form.is_valid():
            data = form.cleaned_data

            try:
                OrderItemService.update_item(
                    item=item,
                    product=data.get("product"),
                    product_name=data.get("product_name", ""),
                    quantity=data.get("quantity"),
                    specifications=data.get("specifications", ""),
                    price=data.get("price"),
                    reference_image=data.get("reference_image"),
                    design_attachment=data.get("design_attachment"),
                    length_cm=data.get("length_cm"),
                    width_cm=data.get("width_cm"),
                    height_cm=data.get("height_cm"),
                    material_preference=data.get("material_preference", ""),
                    colour=data.get("colour", ""),
                    finish=data.get("finish", ""),
                    customer_budget=data.get("customer_budget"),
                    actor=request.user,
                )
            except ValidationError as error:
                form.add_error(None, _validation_message(error))
            else:
                messages.success(
                    request,
                    "Order item updated successfully.",
                )

                return redirect(
                    "orders:order_detail",
                    pk=order.pk,
                )

    else:
        form = OrderItemForm(
            instance=item,
            order_type=order.order_type,
            business_unit=order.business_unit,
        )

    return render(
        request,
        "orders/order_item_form.html",
        {
            "form": form,
            "order": order,
            "item": item,
            "page_title": "Edit Order Item",
        },
    )
# =========================================================
# REMOVE ORDER ITEM
# =========================================================

@login_required
@wpg_permission_required("orders.change_order", feature_code="ORDER_LIST", action="change")
@require_POST
def remove_order_item(request, pk):
    item = get_object_or_404(
        OrderItem.objects.select_related(
            "order",
        ),
        pk=pk,
    )

    order = item.order

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        OrderService.remove_item(
            item
        )

    except ValidationError as error:
        messages.error(
            request,
            _validation_message(error),
        )

    else:
        messages.success(
            request,
            "Order item removed successfully.",
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

# =========================================================
# SUBMIT ORDER
# =========================================================

@login_required
@wpg_permission_required("orders.change_order", feature_code="ORDER_LIST", action="change")
@require_POST
def submit_order(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        OrderService.submit(
            order=order,
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
                f"Order {order.order_number} "
                "submitted successfully."
            ),
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

# =========================================================
# CONFIRM ORDER
# =========================================================

@login_required
@wpg_permission_required("orders.approve_order", feature_code="ORDER_APPROVAL", action="approve")
@require_POST
def confirm_order(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        order, routing_result = (
            OrderService.confirm(
                order=order,
                actor=request.user,
            )
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
                f"Order {order.order_number} "
                "confirmed successfully. "
                f"{routing_result['message']}"
            ),
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )
# =========================================================
# CANCEL ORDER
# =========================================================

@login_required
@wpg_permission_required("orders.approve_order", feature_code="ORDER_APPROVAL", action="approve")
@require_POST
def cancel_order(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    reason = (
        request.POST.get(
            "reason",
            "",
        )
        .strip()
    )

    try:
        OrderService.cancel(
            order=order,
            actor=request.user,
            reason=reason,
        )

    except ValidationError as error:
        messages.error(
            request,
            _validation_message(error),
        )

    else:
        messages.warning(
            request,
            (
                f"Order {order.order_number} "
                "was cancelled."
            ),
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def mark_shipped(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        DeliveryService.mark_shipped(
            order=order,
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
            f"Order {order.order_number} marked as shipped.",
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def deliver_order(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if request.method != "POST":
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    note = (
        request.POST.get("note", "")
        .strip()
    )

    try:
        result = DeliveryService.deliver_order(
            order=order,
            delivered_by=request.user,
            note=note,
        )

    except ValidationError as error:
        messages.error(
            request,
            _validation_message(error),
        )

    else:
        messages.success(
            request,
            result["message"],
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

def _validation_message(error):
    if hasattr(error, "message_dict"):
        messages_list = []

        for field_messages in error.message_dict.values():
            messages_list.extend(field_messages)

        return " ".join(
            str(message)
            for message in messages_list
        )

    if hasattr(error, "messages"):
        return " ".join(
            str(message)
            for message in error.messages
        )

    return str(error)

@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def mark_ready(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if not PermissionService.user_can_access_feature(
        request.user,
        "ORDER_DELIVERY",
        action="edit",
    ):
        messages.error(
            request,
            "You do not have permission to mark orders as ready.",
        )
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        OrderService.mark_ready(
            order=order,
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
                f"Order {order.order_number} "
                "is now ready for delivery."
            ),
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def order_dispatch(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if not PermissionService.user_can_access_feature(
        request.user,
        "ORDER_DELIVERY",
        action="edit",
    ):
        messages.error(
            request,
            "You do not have permission to dispatch orders.",
        )
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        DeliveryService.dispatch_order(
            order=order,
            actor=request.user,
            note=request.POST.get(
                "note",
                "",
            ),
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
                f"Order {order.order_number} "
                "was dispatched successfully."
            ),
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def order_mark_delivered(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if not PermissionService.user_can_access_feature(
        request.user,
        "ORDER_DELIVERY",
        action="approve",
    ):
        messages.error(
            request,
            "You do not have permission to complete deliveries.",
        )
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        result = DeliveryService.mark_delivered(
            order=order,
            actor=request.user,
            note=request.POST.get(
                "note",
                "",
            ),
            fulfil_inventory=True,
            strict_inventory=True,
        )

    except ValidationError as error:
        messages.error(
            request,
            _validation_message(error),
        )

    else:
        messages.success(
            request,
            result["message"],
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def cancel_delivery(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if not PermissionService.user_can_access_feature(
        request.user,
        "ORDER_DELIVERY",
        action="delete",
    ):
        messages.error(
            request,
            "You do not have permission to cancel deliveries.",
        )
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    note = request.POST.get(
        "note",
        "",
    ).strip()

    if not note:
        messages.error(
            request,
            "Provide a reason for cancelling the delivery.",
        )
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        result = DeliveryService.cancel_delivery(
            order=order,
            actor=request.user,
            note=note,
            release_inventory=True,
        )

    except ValidationError as error:
        messages.error(
            request,
            _validation_message(error),
        )

    else:
        messages.warning(
            request,
            result["message"],
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )

    
@login_required
@wpg_permission_required("orders.fulfil_order", feature_code="ORDER_FULFILMENT", action="approve")
@require_POST
def mark_processing(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
    )

    if not PermissionService.user_can_access_feature(
        request.user,
        "ORDER_DELIVERY",
        action="edit",
    ):
        messages.error(
            request,
            "You do not have permission to process orders.",
        )
        return redirect(
            "orders:order_detail",
            pk=order.pk,
        )

    try:
        OrderService.mark_processing(
            order=order,
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
            f"Order {order.order_number} is now processing.",
        )

    return redirect(
        "orders:order_detail",
        pk=order.pk,
    )
