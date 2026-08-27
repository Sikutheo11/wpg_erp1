from django.urls import path
from . import views

app_name="inventory"



urlpatterns=[
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("warehouses/create/", views.warehouse_create, name="warehouse_create"),
    path("warehouses/<int:pk>/edit/", views.warehouse_update, name="warehouse_update"),
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/create/", views.supplier_create, name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.supplier_update, name="supplier_update"),
    path("asset-assignments/", views.asset_assignment_list, name="asset_assignment_list"),
    path("asset-assignments/create/", views.asset_assignment_create, name="asset_assignment_create"),
    path("asset-assignments/<int:pk>/edit/", views.asset_assignment_update, name="asset_assignment_update"),
    

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
    "materials/<int:pk>/",
    views.material_detail,
    name="material_detail"
    ),

    path(
    "materials/<int:pk>/edit/",
    views.material_update,
    name="material_update"
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
    "products/<int:pk>/edit/",
    views.product_update,
    name="product_update"
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
    "assets/<int:pk>/edit/",
    views.asset_update,
    name="asset_update"
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
