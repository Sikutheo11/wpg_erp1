from django.urls import path

from . import views



urlpatterns = [


    # =================================================
    # DASHBOARD
    # =================================================

    path('',
        views.furniture_dashboard,
        name='furniture_dashboard'
    ),



    # =================================================
    # CUSTOMER ORDERS
    # =================================================

    path(
        'orders/',
        views.order_list,
        name='order_list'
    ),


    path(
        'orders/create/',
        views.order_create,
        name='order_create'
    ),



    path(
        'orders/<int:pk>/assign/',
        views.assign_worker,
        name='assign_worker'
    ),



    # =================================================
    # QUOTATION
    # =================================================

    path(
        'orders/<int:pk>/quotation/',
        views.create_quotation,
        name='create_quotation'
    ),



    path(
        'quotations/',
        views.quotation_list,
        name='quotation_list'
    ),



    path(
        'quotations/<int:pk>/approve/',
        views.approve_quotation,
        name='approve_quotation'
    ),



    # =================================================
    # MATERIAL CONSUMPTION
    # =================================================

    path(
        'orders/<int:pk>/materials/add/',
        views.add_material,
        name='add_material'
    ),



    # =================================================
    # LABOUR
    # =================================================

    path(
        'orders/<int:pk>/labour/add/',
        views.add_labour,
        name='add_labour'
    ),



    # =================================================
    # MACHINE
    # =================================================

    path(
        'orders/<int:pk>/machine/add/',
        views.add_machine,
        name='add_machine'
    ),



    # =================================================
    # PRODUCTION OUTPUT
    # =================================================

    path(
        'orders/<int:pk>/output/add/',
        views.add_output,
        name='add_output'
    ),
    path(
    'materials/',
    views.material_list,
    name='material_list'
),


    path(
        'labour/',
        views.labour_list,
        name='labour_list'
    ),


    path(
        'machines/',
        views.machine_list,
        name='machine_list'
    ),


    path(
        'outputs/',
        views.output_list,
        name='output_list'
    ),


    path(
        'reports/',
        views.production_reports,
        name='production_reports'
    ),
    

]