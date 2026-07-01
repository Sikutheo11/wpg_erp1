from django.urls import path
from . import views

app_name="inventory"



urlpatterns=[
    

    path(
    "dashboard/",
    views.inventory_dashboard,
    name="dashboard"
    ),
    
     path(
        "dashboard/",
        views.inventory_dashboard,
        name="inventory_dashboard"
    ),


    path(
    "materials/",
    views.material_list,
    name="material_list"
    ),


    path(
    "materials/create/",
    views.material_create,
    name="material_create"
    ),


    path(
    "products/",
    views.product_list,
    name="product_list"
    ),


    path(
    "products/create/",
    views.product_create,
    name="product_create"
    ),


    path(
    "assets/",
    views.asset_list,
    name="asset_list"
    ),


    path(
    "assets/create/",
    views.asset_create,
    name="asset_create"
    ),


    path(
    "movements/",
    views.movement_list,
    name="movement_list"
    ),


    path(
    "movements/create/",
    views.stock_create,
    name="stock_create"
    ),


    path(
    "reports/low-stock/",
    views.low_stock_report,
    name="low_stock"
    ),


]