from django.urls import path

from . import views


app_name = "ecommerce"


urlpatterns = [
    # Public Ecommerce catalogue
    path("", views.shop, name="home"),
    path("shop/", views.shop, name="shop"),
    path(
        "shop/<slug:slug>/",
        views.product_detail,
        name="product_detail",
    ),

    # Ecommerce management
    path(
        "dashboard/",
        views.ecommerce_dashboard,
        name="ecommerce_dashboard",
    ),
    path(
        "management/products/",
        views.online_product_list,
        name="online_product_list",
    ),
    path(
        "management/products/new/",
        views.online_product_create,
        name="online_product_create",
    ),
    path(
        "management/products/<int:pk>/edit/",
        views.online_product_update,
        name="online_product_update",
    ),
    path(
        "management/products/<int:pk>/toggle-publish/",
        views.toggle_publish,
        name="toggle_publish",
    ),
    path(
        "management/products/<int:pk>/toggle-featured/",
        views.toggle_featured,
        name="toggle_featured",
    ),
    path(
        "management/products/<int:product_pk>/seller/",
        views.seller_product_assignment,
        name="seller_product_assignment",
    ),

    # Marketplace sellers
    path(
        "management/sellers/",
        views.marketplace_seller_list,
        name="marketplace_seller_list",
    ),
    path(
        "management/sellers/new/",
        views.marketplace_seller_create,
        name="marketplace_seller_create",
    ),
    path(
        "management/sellers/<int:pk>/",
        views.marketplace_seller_detail,
        name="marketplace_seller_detail",
    ),

    # Seller settlements
    path(
        "management/settlements/",
        views.seller_settlement_list,
        name="seller_settlement_list",
    ),
    path(
        "management/sellers/<int:seller_pk>/settlements/new/",
        views.seller_settlement_create,
        name="seller_settlement_create",
    ),
    path(
        "management/settlements/<int:pk>/",
        views.seller_settlement_detail,
        name="seller_settlement_detail",
    ),
    path(
        "management/settlements/<int:pk>/approve/",
        views.seller_settlement_approve,
        name="seller_settlement_approve",
    ),
    path(
        "management/settlements/<int:pk>/pay/",
        views.seller_settlement_pay,
        name="seller_settlement_pay",
    ),

    # Cart
    path("cart/", views.cart_detail, name="cart_detail"),
    path(
        "cart/add/<int:product_id>/",
        views.add_to_cart,
        name="add_to_cart",
    ),
    path(
        "cart/<int:product_id>/update/",
        views.update_cart,
        name="update_cart",
    ),
    path(
        "cart/<int:product_id>/remove/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),

    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    path(
        "checkout/<int:checkout_id>/success/",
        views.checkout_success,
        name="checkout_success",
    ),
    path(
        "checkout/<int:checkout_id>/payment/",
        views.checkout_payment,
        name="checkout_payment",
    ),

    # Compatibility routes
    path(
        "order/success/<int:order_id>/",
        views.order_success,
        name="order_success",
    ),
    path(
        "product/<slug:slug>/",
        views.product_detail,
        name="legacy_product_detail",
    ),

    # Customer orders and payments
    path("orders/", views.my_orders, name="my_orders"),
    path(
        "payments/<int:payment_id>/waiting/",
        views.payment_waiting,
        name="payment_waiting",
    ),
    path(
        "payments/<int:payment_id>/confirm/",
        views.payment_confirm,
        name="payment_confirm",
    ),
    path(
        "management/payments/",
        views.payment_list,
        name="payment_list",
    ),

    path(
        "management/reports/",
        views.marketplace_report,
        name="marketplace_report",
    ),
]