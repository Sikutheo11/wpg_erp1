from django.urls import path

from . import planner_views

urlpatterns = [
    path("", planner_views.production_plan_list, name="planner_list"),
    path("new/", planner_views.production_plan_create, name="planner_create"),
    path("orders/<int:order_id>/technical-costing/", planner_views.order_technical_costing, name="order_technical_costing"),
    path("<int:pk>/", planner_views.production_plan_detail, name="planner_detail"),
    path("<int:pk>/edit/", planner_views.production_plan_edit, name="planner_edit"),
    path("<int:pk>/import-bom/", planner_views.production_plan_import_bom, name="planner_import_bom"),
    path("<int:pk>/calculate/", planner_views.production_plan_calculate, name="planner_calculate"),
    path("<int:pk>/finish/", planner_views.production_plan_finish, name="planner_finish"),
    path("<int:pk>/customer-quotation/", planner_views.production_plan_generate_quotation, name="planner_generate_quotation"),
    path("<int:pk>/materials/add/", planner_views.production_plan_add_material, name="planner_add_material"),
    path("<int:pk>/labour/add/", planner_views.production_plan_add_labour, name="planner_add_labour"),
    path("<int:pk>/machines/add/", planner_views.production_plan_add_machine, name="planner_add_machine"),
    path("<int:pk>/additional-costs/add/", planner_views.production_plan_add_additional, name="planner_add_additional"),
]
