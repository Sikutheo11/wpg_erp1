from django.urls import path

from . import views


app_name = "ecommerce"



urlpatterns = [


    # ======================================
    # ECOMMERCE DASHBOARD
    # ======================================

    path(
        "dashboard/",
        views.ecommerce_dashboard,
        name="ecommerce_dashboard"
    ),




    # ======================================
    # ONLINE PRODUCTS
    # ======================================


    path(
        "products/",
        views.online_product_list,
        name="online_product_list"
    ),



    path(
        "products/create/",
        views.online_product_create,
        name="online_product_create"
    ),
    path(
    "product/<slug:slug>/",
    views.product_detail,
    name="product_detail",
    ),    

    # ======================================
    # PUBLISH CONTROL
    # ======================================


    path(
        "products/<int:pk>/toggle-publish/",
        views.toggle_publish,
        name="toggle_publish"
    ),




    # ======================================
    # FEATURE CONTROL
    # ======================================


    path(
        "products/<int:pk>/toggle-featured/",
        views.toggle_featured,
        name="toggle_featured"
    ),
    # PUBLIC SHOP

    path(
        "shop/",
        views.shop,
        name="shop"
    ),



    # PRODUCT DETAIL

    path(
        "shop/<slug:slug>/",
        views.product_detail,
        name="product_detail"
    ),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),
    path("checkout/", views.checkout,name="checkout",),
    path("order/success/<int:order_id>/", views.order_success,name="order_success"),

]