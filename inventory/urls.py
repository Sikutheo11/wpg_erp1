from django.urls import path
from . import views

urlpatterns = [

    # ==================================================
    # DASHBOARD
    # ==================================================

    path('', views.inventory_dashboard, name='inventory_dashboard' ),
    path('materials/', views.material_list, name='material_list' ),
    path('materials/add/', views.material_create, name='material_create' ),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    path('products/',views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/add/', views.asset_create, name='asset_create'),
    path('movements/', views.movement_list, name='movement_list'),
    path('movements/add/', views.stock_create, name='stock_create'),
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    path('materials/<int:pk>/edit/',views.material_update,name='material_update'),
    path('materials/<int:pk>/delete/',views.material_delete,name='material_delete'),
    path('products/<int:pk>/edit/',views.product_update,name='product_update'),
    path('products/<int:pk>/delete/',views.product_delete,name='product_delete'),
    path('assets/<int:pk>/edit/',views.asset_update,name='asset_update'),
    path('assets/<int:pk>/delete/',views.asset_delete,name='asset_delete'),
]