from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db.models import Count, F, Q, Sum
from django.utils.dateparse import parse_date
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)
from django.conf import settings
from django.core import signing
from django.core.signing import (
    BadSignature,
    SignatureExpired,
)
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order

from .cart import Cart
from .dashboard import get_ecommerce_dashboard
from .forms import (
    CheckoutForm,
    EcommercePaymentForm,
    MarketplaceSellerForm,
    OnlineProductForm,
    PaymentConfirmationForm,
    SellerProductAssignmentForm,
    SellerSettlementCreateForm,
    SellerSettlementPaymentForm,
    PaymentRefundForm,
)
from .models import (
    EcommerceCheckout,
    EcommerceCheckoutOrder,
    EcommercePayment,
    MarketplaceOrderLine,
    MarketplaceSeller,
    OnlineProduct,
    SellerProductAssignment,
    SellerSettlement,
)
from .services import (
    EcommerceCheckoutService,
    EcommercePaymentService,
    SellerSettlementService,
)

from .permissions import (
    commission_edit_required,
    marketplace_dashboard_required,
    payment_confirm_required,
    payment_view_required,
    product_add_required,
    product_edit_required,
    product_view_required,
    report_view_required,
    seller_add_required,
    seller_view_required,
    settlement_add_required,
    settlement_approve_required,
    settlement_pay_required,
    settlement_view_required,
    payment_refund_required,
)



def _online_catalogue():
    return (
        OnlineProduct.objects
        .select_related(
            "product",
            "product__category",
        )
        .filter(
            product__is_active=True,
            product__is_published=True,
            product__business_unit__in={
                "FURNITURE",
                "CONSTRUCTION",
                "AGRICULTURE",
            },
        )
    )


def _add_validation_error(form, error):
    if hasattr(error, "message_dict"):
        for field_name, field_errors in error.message_dict.items():
            target = field_name if field_name in form.fields else None
            for message in field_errors:
                form.add_error(target, message)
        return

    for message in error.messages:
        form.add_error(None, message)


def _validation_messages(request, error):
    if hasattr(error, "message_dict"):
        for field_errors in error.message_dict.values():
            for message in field_errors:
                messages.error(request, message)
        return

    for message in error.messages:
        messages.error(request, message)


def _customer_initial(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return {}

    full_name = ""
    get_full_name = getattr(user, "get_full_name", None)
    if callable(get_full_name):
        full_name = get_full_name()

    if not full_name:
        full_name = (
            getattr(user, "name", "")
            or getattr(user, "username", "")
            or getattr(user, "email", "")
        )

    phone = (
        getattr(user, "phone", "")
        or getattr(user, "phone_number", "")
        or getattr(user, "telephone", "")
    )

    return {
        "full_name": full_name,
        "phone": phone,
        "email": getattr(user, "email", ""),
    }


# ---------------------------------------------------------------------------
# Ecommerce management
# ---------------------------------------------------------------------------


@login_required
@marketplace_dashboard_required
def ecommerce_dashboard(request):
    return render(
        request,
        "ecommerce/dashboard.html",
        {
            "dashboard": get_ecommerce_dashboard(request.user),
        },
    )


@login_required
@product_view_required
def online_product_list(request):
    products = (
        OnlineProduct.objects
        .select_related("product", "product__category")
        .order_by("product__business_unit", "product__name")
    )

    business_unit = request.GET.get("business_unit", "").strip().upper()
    purchase_mode = request.GET.get("purchase_mode", "").strip().upper()
    search = request.GET.get("q", "").strip()

    if business_unit:
        products = products.filter(product__business_unit=business_unit)
    if purchase_mode:
        products = products.filter(purchase_mode=purchase_mode)
    if search:
        products = products.filter(
            Q(title__icontains=search)
            | Q(product__name__icontains=search)
            | Q(product__product_code__icontains=search)
        )

    return render(
        request,
        "ecommerce/product_list.html",
        {
            "products": products,
            "business_units": (
                ("FURNITURE", "Furniture & Manufacturing"),
                ("CONSTRUCTION", "Construction"),
                ("AGRICULTURE", "Agriculture / Poultry"),
            ),
            "purchase_modes": OnlineProduct.PURCHASE_MODES,
            "selected_business_unit": business_unit,
            "selected_purchase_mode": purchase_mode,
            "search": search,
        },
    )


@login_required
@product_add_required
def online_product_create(request):
    form = OnlineProductForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():
        online_product = form.save()
        messages.success(
            request,
            f"{online_product.display_title} was added to Ecommerce.",
        )
        return redirect("ecommerce:online_product_list")

    return render(
        request,
        "ecommerce/product_form.html",
        {
            "form": form,
            "title": "Create Online Product",
            "submit_label": "Save Online Product",
        },
    )


@login_required
@product_edit_required
def online_product_update(request, pk):
    online_product = get_object_or_404(
        OnlineProduct.objects.select_related("product"),
        pk=pk,
    )
    form = OnlineProductForm(
        request.POST or None,
        request.FILES or None,
        instance=online_product,
    )

    if request.method == "POST" and form.is_valid():
        online_product = form.save()
        messages.success(
            request,
            f"{online_product.display_title} was updated.",
        )
        return redirect("ecommerce:online_product_list")

    return render(
        request,
        "ecommerce/product_form.html",
        {
            "form": form,
            "online_product": online_product,
            "title": f"Edit {online_product.display_title}",
            "submit_label": "Update Online Product",
        },
    )


@login_required
@product_edit_required
@require_POST
def toggle_publish(request, pk):
    online_product = get_object_or_404(
        OnlineProduct.objects.select_related("product"),
        pk=pk,
    )
    product = online_product.product
    product.is_published = not product.is_published
    product.save(update_fields=["is_published", "updated_at"])

    state = "published" if product.is_published else "unpublished"
    messages.success(
        request,
        f"{online_product.display_title} was {state}.",
    )
    return redirect("ecommerce:online_product_list")


@login_required
@product_edit_required
@require_POST
def toggle_featured(request, pk):
    online_product = get_object_or_404(
        OnlineProduct.objects.select_related("product"),
        pk=pk,
    )
    product = online_product.product
    product.is_featured = not product.is_featured
    product.save(update_fields=["is_featured", "updated_at"])

    state = "featured" if product.is_featured else "unfeatured"
    messages.success(
        request,
        f"{online_product.display_title} was {state}.",
    )
    return redirect("ecommerce:online_product_list")


# ---------------------------------------------------------------------------
# Public catalogue
# ---------------------------------------------------------------------------


def shop(request):
    products = _online_catalogue()
    search = request.GET.get("q", "").strip()
    business_unit = request.GET.get("business_unit", "").strip().upper()
    category_id = request.GET.get("category", "").strip()

    if search:
        products = products.filter(
            Q(title__icontains=search)
            | Q(short_description__icontains=search)
            | Q(product__name__icontains=search)
            | Q(product__description__icontains=search)
            | Q(product__product_code__icontains=search)
        )

    if business_unit in {
        "FURNITURE",
        "CONSTRUCTION",
        "AGRICULTURE",
    }:
        products = products.filter(product__business_unit=business_unit)
    else:
        business_unit = ""

    if category_id.isdigit():
        products = products.filter(product__category_id=category_id)

    products = products.order_by(
        "-product__is_featured",
        "product__business_unit",
        "product__name",
    )
    featured_products = products.filter(
        product__is_featured=True
    )[:8]

    return render(
        request,
        "ecommerce/shop.html",
        {
            "products": products,
            "featured_products": featured_products,
            "search": search,
            "selected_business_unit": business_unit,
            "selected_category": category_id,
            "cart": Cart(request),
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        _online_catalogue(),
        slug=slug,
    )

    OnlineProduct.objects.filter(pk=product.pk).update(
        views=F("views") + 1
    )
    product.views += 1

    related_products = (
        _online_catalogue()
        .filter(product__business_unit=product.product.business_unit)
        .exclude(pk=product.pk)
        .order_by("-product__is_featured", "product__name")[:4]
    )

    return render(
        request,
        "ecommerce/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "cart": Cart(request),
        },
    )


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


@require_POST
def add_to_cart(request, product_id):
    cart = Cart(request)

    try:
        cart.add(
            product_id,
            request.POST.get("quantity", 1),
        )
    except ValidationError as error:
        _validation_messages(request, error)
    else:
        messages.success(request, "Product added to your cart.")

    next_url = request.POST.get("next", "").strip()
    if next_url.startswith("/"):
        return redirect(next_url)

    return redirect("ecommerce:cart_detail")


@require_POST
def remove_from_cart(request, product_id):
    Cart(request).remove(product_id)
    messages.success(request, "Product removed from your cart.")
    return redirect("ecommerce:cart_detail")


def cart_detail(request):
    cart = Cart(request)
    items = cart.items()

    return render(
        request,
        "ecommerce/cart.html",
        {
            "cart": cart,
            "items": items,
            "grouped_items": cart.grouped_items(),
            "total": cart.total,
        },
    )


@require_POST
def update_cart(request, product_id):
    cart = Cart(request)

    try:
        cart.update(
            product_id,
            request.POST.get("quantity", 1),
        )
    except ValidationError as error:
        _validation_messages(request, error)
    else:
        messages.success(request, "Cart quantity updated.")

    return redirect("ecommerce:cart_detail")


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------


@login_required
def checkout(request):
    cart = Cart(request)

    if not cart:
        messages.info(request, "Your cart is empty.")
        return redirect("ecommerce:cart_detail")

    if request.method == "POST":
        form = CheckoutForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            try:
                result = EcommerceCheckoutService.create_checkout(
                    cart=cart,
                    customer_data=form.cleaned_data,
                    user=request.user,
                    actor=request.user,
                )
            except ValidationError as error:
                _add_validation_error(form, error)
            else:
                checkout_object = result["checkout"]
                messages.success(
                    request,
                    (
                        f"Checkout {checkout_object.checkout_number} "
                        "was created successfully."
                    ),
                )
                return redirect(
                    "ecommerce:checkout_success",
                    checkout_id=checkout_object.pk,
                )
    else:
        form = CheckoutForm(
            user=request.user,
            initial=_customer_initial(request.user),
        )

    return render(
        request,
        "ecommerce/checkout.html",
        {
            "form": form,
            "cart": cart,
            "cart_items": cart.items(),
            "grouped_items": cart.grouped_items(),
            "total": cart.total,
        },
    )


@login_required
def checkout_success(request, checkout_id):
    checkouts = (
        EcommerceCheckout.objects
        .select_related("user")
        .prefetch_related(
            "checkout_orders",
            "checkout_orders__order",
            "checkout_orders__order__items",
            "checkout_orders__order__items__product",
        )
    )

    if not request.user.is_superuser:
        checkouts = checkouts.filter(user=request.user)

    checkout_object = get_object_or_404(
        checkouts,
        pk=checkout_id,
    )

    return render(
        request,
        "ecommerce/order_success.html",
        {
            "checkout": checkout_object,
            "checkout_orders": checkout_object.checkout_orders.all(),
        },
    )

@login_required
def my_orders(request):
    checkouts = (
        EcommerceCheckout.objects
        .filter(user=request.user)
        .prefetch_related(
            "checkout_orders",
            "checkout_orders__order",
            "checkout_orders__order__items",
        )
        .order_by("-created_at", "-pk")
    )

    return render(
        request,
        "ecommerce/my_orders.html",
        {
            "checkouts": checkouts,
        },
    )


@login_required
def order_success(request, order_id):
    """
    Compatibility redirect for legacy Ecommerce success URLs.
    """

    checkout_link = (
        EcommerceCheckoutOrder.objects
        .select_related("checkout", "checkout__user")
        .filter(order_id=order_id)
        .first()
    )

    if checkout_link is not None:
        if (
            not request.user.is_superuser
            and checkout_link.checkout.user_id != request.user.pk
        ):
            raise Http404("Checkout not found.")

        return redirect(
            "ecommerce:checkout_success",
            checkout_id=checkout_link.checkout_id,
        )

    orders = Order.objects.select_related("user")
    if not request.user.is_superuser:
        orders = orders.filter(user=request.user)

    order = get_object_or_404(orders, pk=order_id)
    return render(
        request,
        "ecommerce/order_success.html",
        {
            "order": order,
            "legacy_order": True,
        },
    )

def _validation_messages(request, error):
    if hasattr(error, "message_dict"):
        for errors in error.message_dict.values():
            for message in errors:
                messages.error(request, message)
        return
    for message in error.messages:
        messages.error(request, message)


def _checkout_for_user(request, checkout_id):
    queryset = EcommerceCheckout.objects.prefetch_related(
        "payments",
        "checkout_orders__order",
    )
    if not (request.user.is_staff or request.user.is_superuser):
        queryset = queryset.filter(user=request.user)
    return get_object_or_404(queryset, pk=checkout_id)


def _payment_for_user(request, payment_id):
    queryset = EcommercePayment.objects.select_related(
        "checkout",
        "checkout__user",
        "customer_advance",
    )
    if not (request.user.is_staff or request.user.is_superuser):
        queryset = queryset.filter(checkout__user=request.user)
    return get_object_or_404(queryset, pk=payment_id)

PAYMENT_CALLBACK_SALT = (
    "ecommerce.payment.provider-callback.v1"
)


def _payment_callback_url(payment):
    base_url = getattr(
        settings,
        "ECOMMERCE_PAYMENT_CALLBACK_BASE_URL",
        "",
    ).strip().rstrip("/")

    if not base_url:
        return ""

    token = signing.dumps(
        {
            "payment_id": payment.pk,
            "provider": payment.provider,
        },
        salt=PAYMENT_CALLBACK_SALT,
        compress=True,
    )

    callback_path = reverse(
        "ecommerce:payment_provider_callback",
        kwargs={"token": token},
    )

    return f"{base_url}{callback_path}"

@login_required
@require_http_methods(["GET", "POST"])
def checkout_payment(request, checkout_id):
    checkout = _checkout_for_user(request, checkout_id)
    order_statuses = list(
        checkout.checkout_orders.values_list(
            "order__status",
            flat=True,
        )
    )

    if (
        checkout.status == "CANCELLED"
        or (
            order_statuses
            and all(
                status == "CANCELLED"
                for status in order_statuses
            )
        )
    ):
        messages.error(
            request,
            "This checkout was cancelled and can no longer be paid.",
        )
        return redirect(
            "ecommerce:checkout_success",
            checkout_id=checkout.pk,
        )

    confirmed = checkout.payments.filter(
        status=EcommercePayment.CONFIRMED
    ).first()
    if confirmed is not None:
        return redirect(
            "ecommerce:payment_waiting",
            payment_id=confirmed.pk,
        )

    active_payment = checkout.payments.filter(
        status__in={
            EcommercePayment.INITIATED,
            EcommercePayment.PENDING,
        }
    ).order_by("-pk").first()

    if request.method == "POST":
        form = EcommercePaymentForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                payment, unused_created = (
                    EcommercePaymentService.initiate_payment(
                        checkout=checkout,
                        method=form.cleaned_data["method"],
                        provider=form.cleaned_data["provider"],
                        customer_reference=form.cleaned_data[
                            "customer_reference"
                        ],
                        proof_image=form.cleaned_data.get("proof_image"),
                        notes=form.cleaned_data.get("notes", ""),
                        idempotency_key=(
                            f"CHECKOUT_PAYMENT_ATTEMPT:{checkout.pk}:"
                            f"{form.cleaned_data['provider']}:"
                            f"{form.cleaned_data['customer_reference']}"
                        ),
                        actor=request.user,
                    )
                )
                callback_url = _payment_callback_url(payment)

                payment, unused_changed = (
                    EcommercePaymentService
                    .request_provider_payment(
                        payment=payment,
                        callback_url=callback_url,
                        actor=request.user,
                    )
                )
            except ValidationError as error:
                _validation_messages(request, error)
            else:
                messages.success(
                    request,
                    "Payment submitted and is awaiting confirmation.",
                )
                return redirect(
                    "ecommerce:payment_waiting",
                    payment_id=payment.pk,
                )
    else:
        initial = {}
        if active_payment is not None:
            initial = {
                "method": active_payment.method,
                "provider": active_payment.provider,
                "customer_reference": (
                    active_payment.customer_reference
                ),
                "notes": active_payment.notes,
            }
        form = EcommercePaymentForm(initial=initial)

    return render(
        request,
        "ecommerce/payments/payment_form.html",
        {
            "checkout": checkout,
            "form": form,
            "active_payment": active_payment,
        },
    )


@login_required
def payment_waiting(request, payment_id):
    payment = _payment_for_user(request, payment_id)
    return render(
        request,
        "ecommerce/payments/payment_waiting.html",
            {
            "payment": payment,
            "checkout": payment.checkout,
            "manual_confirmation_allowed": (
                not EcommercePaymentService.is_automated_provider(
                    payment.provider
                )
            ),
        },
    )

@login_required
@require_POST
def payment_status_refresh(request, payment_id):
    payment = _payment_for_user(
        request,
        payment_id,
    )

    try:
        payment, changed = (
            EcommercePaymentService.check_provider_status(
                payment=payment,
                actor=request.user,
            )
        )
    except ValidationError as error:
        _validation_messages(request, error)
    else:
        payment.refresh_from_db()

        if payment.status == EcommercePayment.CONFIRMED:
            messages.success(
                request,
                (
                    f"Payment {payment.payment_number} "
                    "has been confirmed successfully."
                ),
            )

        elif payment.status == EcommercePayment.FAILED:
            messages.error(
                request,
                "The payment provider reported that payment failed.",
            )

        elif payment.status == EcommercePayment.PENDING:
            messages.info(
                request,
                "Payment is still awaiting provider confirmation.",
            )

    return redirect(
        "ecommerce:payment_waiting",
        payment_id=payment.pk,
    )

@csrf_exempt
@require_POST
def payment_provider_callback(request, token):
    try:
        callback_data = signing.loads(
            token,
            salt=PAYMENT_CALLBACK_SALT,
            max_age=60 * 60 * 24 * 7,
        )
    except SignatureExpired:
        return JsonResponse(
            {"detail": "Callback token expired."},
            status=410,
        )
    except BadSignature:
        return JsonResponse(
            {"detail": "Invalid callback token."},
            status=400,
        )

    payment = (
        EcommercePayment.objects
        .select_related("checkout")
        .filter(
            pk=callback_data.get("payment_id"),
            provider=callback_data.get("provider"),
        )
        .first()
    )

    if payment is None:
        return JsonResponse(
            {"detail": "Payment not found."},
            status=404,
        )

    if not EcommercePaymentService.is_automated_provider(
        payment.provider
    ):
        return JsonResponse(
            {
                "detail": (
                    "This payment does not accept "
                    "provider callbacks."
                )
            },
            status=400,
        )

    payment.callback_received_at = timezone.now()
    payment.save(
        update_fields=[
            "callback_received_at",
            "updated_at",
        ]
    )

    if payment.status in {
        EcommercePayment.CONFIRMED,
        EcommercePayment.FAILED,
        EcommercePayment.CANCELLED,
        EcommercePayment.REFUNDED,
    }:
        return JsonResponse(
            {
                "accepted": True,
                "payment_status": payment.status,
            }
        )

    try:
        payment, unused_changed = (
            EcommercePaymentService
            .check_provider_status(
                payment=payment,
                actor=None,
            )
        )
    except ValidationError as error:
        return JsonResponse(
            {
                "accepted": False,
                "errors": error.messages,
            },
            status=409,
        )

    payment.refresh_from_db()

    return JsonResponse(
        {
            "accepted": True,
            "payment_status": payment.status,
            "provider_status": payment.provider_status,
        }
    )

@login_required
@payment_confirm_required
@require_http_methods(["GET", "POST"])
def payment_confirm(request, payment_id):
    # if not (request.user.is_staff or request.user.is_superuser):
    #     raise PermissionDenied(
    #         "Only authorized staff can confirm Ecommerce payments."
    #     )

    payment = _payment_for_user(request, payment_id)
    if EcommercePaymentService.is_automated_provider(
        payment.provider
    ):
        messages.error(
            request,
            (
                f"{payment.get_provider_display()} payment "
                "cannot be confirmed manually. Refresh its status "
                "to obtain confirmation from the provider."
            ),
        )
        return redirect(
            "ecommerce:payment_waiting",
            payment_id=payment.pk,
        )
    initial_reference = payment.provider_reference

    if request.method == "POST":
        form = PaymentConfirmationForm(request.POST)
        if form.is_valid():
            try:
                payment, unused_changed = (
                    EcommercePaymentService.confirm_payment(
                        payment=payment,
                        provider_reference=form.cleaned_data[
                            "provider_reference"
                        ],
                        actor=request.user,
                    )
                )
            except ValidationError as error:
                _validation_messages(request, error)
            else:
                messages.success(
                    request,
                    (
                        f"Payment {payment.payment_number} confirmed. "
                        "The customer orders were released."
                    ),
                )
                return redirect(
                    "ecommerce:payment_waiting",
                    payment_id=payment.pk,
                )
    else:
        form = PaymentConfirmationForm(
            initial={"provider_reference": initial_reference}
        )

    return render(
        request,
        "ecommerce/payments/payment_confirm.html",
        {
            "payment": payment,
            "checkout": payment.checkout,
            "form": form,
        },
    )

@login_required
@payment_refund_required
@require_http_methods(["GET", "POST"])
def payment_refund(request, payment_id):
    payment = get_object_or_404(
        EcommercePayment.objects.select_related(
            "checkout",
            "checkout__user",
            "customer_advance",
        ),
        pk=payment_id,
    )

    if payment.status == EcommercePayment.REFUNDED:
        messages.info(
            request,
            (
                f"Payment {payment.payment_number} "
                "has already been refunded."
            ),
        )
        return redirect(
            "ecommerce:payment_waiting",
            payment_id=payment.pk,
        )

    if payment.status != EcommercePayment.CONFIRMED:
        messages.error(
            request,
            (
                "Only a confirmed Ecommerce payment "
                "can be refunded."
            ),
        )
        return redirect(
            "ecommerce:payment_waiting",
            payment_id=payment.pk,
        )

    form = PaymentRefundForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        try:
            payment, refund_entry, created = (
                EcommercePaymentService.refund_payment(
                    payment=payment,
                    reason=form.cleaned_data["reason"],
                    actor=request.user,
                )
            )

        except ValidationError as error:
            _add_validation_error(
                form,
                error,
            )

        else:
            if created:
                messages.success(
                    request,
                    (
                        f"Payment {payment.payment_number} "
                        f"for {payment.amount} RWF was "
                        "refunded successfully. "
                        "The related Enterprise Order(s) "
                        "may now be cancelled."
                    ),
                )
            else:
                messages.info(
                    request,
                    "This payment was already refunded.",
                )

            return redirect(
                "ecommerce:payment_waiting",
                payment_id=payment.pk,
            )

    return render(
        request,
        "ecommerce/payments/payment_refund.html",
        {
            "payment": payment,
            "checkout": payment.checkout,
            "form": form,
        },
    )

@login_required
@payment_view_required
def payment_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied(
            "Only authorized staff can manage Ecommerce payments."
        )

    payments = (
        EcommercePayment.objects
        .select_related(
            "checkout",
            "checkout__user",
            "customer_advance",
            "confirmed_by",
        )
        .order_by("-initiated_at", "-pk")
    )

    status = request.GET.get("status", "").strip().upper()
    method = request.GET.get("method", "").strip().upper()
    search = request.GET.get("q", "").strip()

    valid_statuses = {
        code for code, unused_label in EcommercePayment.STATUSES
    }
    valid_methods = {
        code for code, unused_label in EcommercePayment.METHODS
    }

    if status in valid_statuses:
        payments = payments.filter(status=status)
    else:
        status = ""

    if method in valid_methods:
        payments = payments.filter(method=method)
    else:
        method = ""

    if search:
        payments = payments.filter(
            Q(payment_number__icontains=search)
            | Q(checkout__checkout_number__icontains=search)
            | Q(checkout__customer_name__icontains=search)
            | Q(checkout__customer_phone__icontains=search)
            | Q(customer_reference__icontains=search)
            | Q(provider_reference__icontains=search)
        )

    return render(
        request,
        "ecommerce/payments/payment_list.html",
        {
            "payments": payments,
            "statuses": EcommercePayment.STATUSES,
            "methods": EcommercePayment.METHODS,
            "selected_status": status,
            "selected_method": method,
            "search": search,
        },
    )

# ---------------------------------------------------------------------------
# Marketplace sellers, commissions and settlements
# ---------------------------------------------------------------------------


@login_required
@seller_view_required
def marketplace_seller_list(request):
    _require_marketplace_staff(request)

    sellers = (
        MarketplaceSeller.objects
        .select_related(
            "poultry_farm",
            "payable_account",
        )
        .annotate(
            gross_sales=Sum("order_lines__gross_amount"),
            commission_total=Sum(
                "order_lines__commission_amount"
            ),
            payable_total=Sum(
                "order_lines__seller_net_amount"
            ),
        )
        .order_by("name", "code")
    )

    seller_type = request.GET.get(
        "seller_type",
        "",
    ).strip().upper()
    search = request.GET.get("q", "").strip()

    valid_types = {
        code
        for code, unused_label
        in MarketplaceSeller.SELLER_TYPES
    }

    if seller_type in valid_types:
        sellers = sellers.filter(
            seller_type=seller_type
        )
    else:
        seller_type = ""

    if search:
        sellers = sellers.filter(
            Q(code__icontains=search)
            | Q(name__icontains=search)
            | Q(contact_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(poultry_farm__name__icontains=search)
        )

    return render(
        request,
        "ecommerce/sellers/seller_list.html",
        {
            "sellers": sellers,
            "seller_types": (
                MarketplaceSeller.SELLER_TYPES
            ),
            "selected_seller_type": seller_type,
            "search": search,
        },
    )


@login_required
@seller_add_required
@require_http_methods(["GET", "POST"])
def marketplace_seller_create(request):
    _require_marketplace_staff(request)

    form = MarketplaceSellerForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        seller = form.save(commit=False)
        seller.created_by = request.user

        try:
            seller.full_clean()
            seller.save()
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(
                request,
                f"Seller {seller.name} created successfully.",
            )
            return redirect(
                "ecommerce:marketplace_seller_detail",
                pk=seller.pk,
            )

    return render(
        request,
        "ecommerce/sellers/seller_form.html",
        {
            "form": form,
            "title": "Create Marketplace Seller",
        },
    )


@login_required
@seller_view_required
def marketplace_seller_detail(request, pk):
    _require_marketplace_staff(request)

    seller = get_object_or_404(
        MarketplaceSeller.objects.select_related(
            "poultry_farm",
            "payable_account",
            "created_by",
        ),
        pk=pk,
    )

    assignments = (
        seller.product_assignments
        .select_related(
            "online_product__product",
        )
        .order_by(
            "online_product__product__business_unit",
            "online_product__product__name",
        )
    )

    sale_lines = (
        seller.order_lines
        .select_related(
            "order_item__order",
            "online_product__product",
            "farm",
        )
        .order_by("-created_at", "-pk")
    )

    eligible_lines = sale_lines.filter(
        settlement_status=(
            MarketplaceOrderLine.ELIGIBLE
        ),
        settlement_line__isnull=True,
    )

    totals = sale_lines.aggregate(
        gross=Sum("gross_amount"),
        commission=Sum("commission_amount"),
        payable=Sum("seller_net_amount"),
    )

    eligible_totals = eligible_lines.aggregate(
        gross=Sum("gross_amount"),
        commission=Sum("commission_amount"),
        payable=Sum("seller_net_amount"),
    )

    settlements = (
        seller.settlements
        .select_related("journal_entry")
        .order_by("-created_at", "-pk")
    )

    return render(
        request,
        "ecommerce/sellers/seller_detail.html",
        {
            "seller": seller,
            "assignments": assignments,
            "sale_lines": sale_lines[:50],
            "eligible_lines": eligible_lines,
            "settlements": settlements,
            "totals": totals,
            "eligible_totals": eligible_totals,
        },
    )


@login_required
@commission_edit_required
@require_http_methods(["GET", "POST"])
def seller_product_assignment(request, product_pk):
    _require_marketplace_staff(request)

    online_product = get_object_or_404(
        OnlineProduct.objects.select_related(
            "product"
        ),
        pk=product_pk,
    )

    assignment = (
        SellerProductAssignment.objects
        .filter(online_product=online_product)
        .first()
    )

    form = SellerProductAssignmentForm(
        request.POST or None,
        instance=assignment,
        online_product=online_product,
    )

    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.online_product = online_product

        try:
            assignment.full_clean()
            assignment.save()
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(
                request,
                (
                    f"Seller and commission for "
                    f"{online_product.display_title} saved."
                ),
            )
            return redirect(
                "ecommerce:online_product_list"
            )

    return render(
        request,
        "ecommerce/sellers/product_assignment_form.html",
        {
            "form": form,
            "online_product": online_product,
            "assignment": assignment,
        },
    )


@login_required
@settlement_add_required
@require_http_methods(["GET", "POST"])
def seller_settlement_create(request, seller_pk):
    _require_marketplace_staff(request)

    seller = get_object_or_404(
        MarketplaceSeller,
        pk=seller_pk,
        seller_type=MarketplaceSeller.INDEPENDENT,
        is_active=True,
    )

    form = SellerSettlementCreateForm(
        request.POST or None,
        seller=seller,
    )

    if request.method == "POST" and form.is_valid():
        try:
            settlement = (
                SellerSettlementService.create_settlement(
                    seller=seller,
                    line_ids=[
                        line.pk
                        for line in form.cleaned_data[
                            "sale_lines"
                        ]
                    ],
                    actor=request.user,
                    notes=form.cleaned_data["notes"],
                )
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(
                request,
                (
                    f"Settlement "
                    f"{settlement.settlement_number} created."
                ),
            )
            return redirect(
                "ecommerce:seller_settlement_detail",
                pk=settlement.pk,
            )

    return render(
        request,
        "ecommerce/settlements/settlement_form.html",
        {
            "seller": seller,
            "form": form,
        },
    )


@login_required
@settlement_view_required
def seller_settlement_detail(request, pk):
    _require_marketplace_staff(request)

    settlement = get_object_or_404(
        SellerSettlement.objects.select_related(
            "seller",
            "seller__poultry_farm",
            "journal_entry",
            "created_by",
            "approved_by",
            "paid_by",
        ).prefetch_related(
            "lines",
            "lines__marketplace_order_line",
            (
                "lines__marketplace_order_line"
                "__order_item__order"
            ),
        ),
        pk=pk,
    )

    return render(
        request,
        "ecommerce/settlements/settlement_detail.html",
        {
            "settlement": settlement,
            "lines": settlement.lines.all(),
        },
    )


@login_required
@settlement_approve_required
@require_POST
def seller_settlement_approve(request, pk):
    _require_marketplace_staff(request)

    settlement = get_object_or_404(
        SellerSettlement,
        pk=pk,
    )

    try:
        settlement, changed = (
            SellerSettlementService.approve_settlement(
                settlement=settlement,
                actor=request.user,
            )
        )
    except ValidationError as error:
        _validation_messages(request, error)
    else:
        if changed:
            messages.success(
                request,
                (
                    f"Settlement "
                    f"{settlement.settlement_number} approved."
                ),
            )
        else:
            messages.info(
                request,
                "This settlement was already approved.",
            )

    return redirect(
        "ecommerce:seller_settlement_detail",
        pk=pk,
    )


@login_required
@settlement_approve_required
@require_POST
def seller_settlement_cancel(request, pk):
    _require_marketplace_staff(request)

    settlement = get_object_or_404(
        SellerSettlement,
        pk=pk,
    )
    reason = request.POST.get(
        "reason",
        "",
    ).strip()

    try:
        settlement, changed = (
            SellerSettlementService.cancel_settlement(
                settlement=settlement,
                actor=request.user,
                reason=reason,
            )
        )
    except ValidationError as error:
        _validation_messages(request, error)
    else:
        if changed:
            messages.success(
                request,
                (
                    f"Settlement "
                    f"{settlement.settlement_number} cancelled. "
                    "Its sale lines are eligible again."
                ),
            )
        else:
            messages.info(
                request,
                "This settlement was already cancelled.",
            )

    return redirect(
        "ecommerce:seller_settlement_detail",
        pk=pk,
    )

@login_required
@settlement_pay_required
@require_http_methods(["GET", "POST"])
def seller_settlement_pay(request, pk):
    settlement = get_object_or_404(
        SellerSettlement.objects.select_related(
            "seller",
        ),
        pk=pk,
    )

    form = SellerSettlementPaymentForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        try:
            settlement, created = (
                SellerSettlementService.pay_settlement(
                    settlement=settlement,
                    payment_method=form.cleaned_data[
                        "payment_method"
                    ],
                    payment_reference=form.cleaned_data[
                        "payment_reference"
                    ],
                    payment_date=form.cleaned_data[
                        "payment_date"
                    ],
                    actor=request.user,
                )
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            if created:
                messages.success(
                    request,
                    (
                        f"{settlement.total_payable} RWF "
                        f"paid to {settlement.seller.name}."
                    ),
                )
            else:
                messages.info(
                    request,
                    "This settlement was already paid.",
                )

            return redirect(
                "ecommerce:seller_settlement_detail",
                pk=settlement.pk,
            )

    return render(
        request,
        "ecommerce/settlements/settlement_payment_form.html",
        {
            "settlement": settlement,
            "form": form,
        },
    )

@login_required
@settlement_view_required
def seller_settlement_list(request):
    settlements = (
        SellerSettlement.objects
        .select_related(
            "seller",
            "seller__poultry_farm",
            "journal_entry",
            "created_by",
            "approved_by",
            "paid_by",
        )
        .prefetch_related("lines")
        .order_by("-created_at", "-pk")
    )

    status = request.GET.get(
        "status",
        "",
    ).strip().upper()

    seller_id = request.GET.get(
        "seller",
        "",
    ).strip()

    search = request.GET.get(
        "q",
        "",
    ).strip()

    valid_statuses = {
        code
        for code, unused_label
        in SellerSettlement.STATUSES
    }

    if status in valid_statuses:
        settlements = settlements.filter(
            status=status
        )
    else:
        status = ""

    if seller_id.isdigit():
        settlements = settlements.filter(
            seller_id=int(seller_id)
        )
    else:
        seller_id = ""

    if search:
        settlements = settlements.filter(
            Q(
                settlement_number__icontains=search
            )
            | Q(seller__code__icontains=search)
            | Q(seller__name__icontains=search)
            | Q(
                seller__poultry_farm__name__icontains=search
            )
            | Q(payment_reference__icontains=search)
        )

    totals = settlements.aggregate(
        gross=Sum("total_gross"),
        commission=Sum("total_commission"),
        payable=Sum("total_payable"),
    )

    sellers = (
        MarketplaceSeller.objects
        .filter(
            seller_type=(
                MarketplaceSeller.INDEPENDENT
            ),
            is_active=True,
        )
        .select_related("poultry_farm")
        .order_by("name")
    )

    return render(
        request,
        "ecommerce/settlements/settlement_list.html",
        {
            "settlements": settlements,
            "statuses": SellerSettlement.STATUSES,
            "sellers": sellers,
            "selected_status": status,
            "selected_seller": seller_id,
            "search": search,
            "totals": totals,
        },
    )

@login_required
@report_view_required
def marketplace_report(request):
    sale_lines = (
        MarketplaceOrderLine.objects
        .select_related(
            "seller",
            "farm",
            "order_item__order",
            "online_product__product",
        )
        .order_by("-created_at", "-pk")
    )

    seller_id = request.GET.get(
        "seller",
        "",
    ).strip()

    farm_id = request.GET.get(
        "farm",
        "",
    ).strip()

    settlement_status = request.GET.get(
        "status",
        "",
    ).strip().upper()

    date_from_value = request.GET.get(
        "date_from",
        "",
    ).strip()

    date_to_value = request.GET.get(
        "date_to",
        "",
    ).strip()

    valid_statuses = {
        code
        for code, unused_label
        in MarketplaceOrderLine.STATUSES
    }

    if seller_id.isdigit():
        sale_lines = sale_lines.filter(
            seller_id=int(seller_id)
        )
    else:
        seller_id = ""

    if farm_id.isdigit():
        sale_lines = sale_lines.filter(
            farm_id=int(farm_id)
        )
    else:
        farm_id = ""

    if settlement_status in valid_statuses:
        sale_lines = sale_lines.filter(
            settlement_status=settlement_status
        )
    else:
        settlement_status = ""

    date_from = parse_date(date_from_value)
    date_to = parse_date(date_to_value)

    if date_from:
        sale_lines = sale_lines.filter(
            created_at__date__gte=date_from
        )
    else:
        date_from_value = ""

    if date_to:
        sale_lines = sale_lines.filter(
            created_at__date__lte=date_to
        )
    else:
        date_to_value = ""

    totals = sale_lines.aggregate(
        order_count=Count(
            "order_item__order_id",
            distinct=True,
        ),
        sale_line_count=Count("id"),
        quantity=Sum("quantity"),
        gross=Sum("gross_amount"),
        commission=Sum("commission_amount"),
        payable=Sum("seller_net_amount"),
    )

    seller_performance = (
        sale_lines
        .values(
            "seller_id",
            "seller_name",
            "seller__seller_type",
            "farm_id",
            "farm__name",
        )
        .annotate(
            order_count=Count(
                "order_item__order_id",
                distinct=True,
            ),
            sale_line_count=Count("id"),
            quantity=Sum("quantity"),
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            payable=Sum("seller_net_amount"),
        )
        .order_by("-gross", "seller_name")
    )

    product_performance = (
        sale_lines
        .values(
            "online_product_id",
            "product_name",
            (
                "online_product__product"
                "__business_unit"
            ),
        )
        .annotate(
            order_count=Count(
                "order_item__order_id",
                distinct=True,
            ),
            quantity=Sum("quantity"),
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            payable=Sum("seller_net_amount"),
        )
        .order_by("-gross", "product_name")
    )

    sellers = (
        MarketplaceSeller.objects
        .filter(is_active=True)
        .select_related("poultry_farm")
        .order_by("name")
    )

    farms = (
        MarketplaceSeller.objects
        .filter(
            poultry_farm__isnull=False,
            poultry_farm__is_active=True,
        )
        .values(
            "poultry_farm_id",
            "poultry_farm__name",
        )
        .distinct()
        .order_by("poultry_farm__name")
    )

    return render(
        request,
        "ecommerce/reports/marketplace_report.html",
        {
            "sale_lines": sale_lines[:100],
            "seller_performance": seller_performance,
            "product_performance": product_performance,
            "totals": totals,
            "sellers": sellers,
            "farms": farms,
            "statuses": MarketplaceOrderLine.STATUSES,
            "selected_seller": seller_id,
            "selected_farm": farm_id,
            "selected_status": settlement_status,
            "date_from": date_from_value,
            "date_to": date_to_value,
        },
    )
