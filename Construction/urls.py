from django.urls import path
from . import views


urlpatterns = [
    path('', views.construction_dashboard, name='construction_dashboard'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/add/',views.project_create,name='project_create'),
    path('projects/<int:pk>/',views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_update, name='project_update'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('sites/', views.site_list, name='site_list'),
    path('sites/add/', views.site_create,name='site_create'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/add/', views.task_create, name='task_create'),
    path('materials/', views.material_usage_list, name='material_usage_list'),
    path('materials/add/', views.material_usage_create, name='material_usage_create'),
    path('assets/', views.asset_usage_list, name='asset_usage_list'),
    path('assets/add/', views.asset_usage_create, name='asset_usage_create'),
    path('labour/', views.labour_list, name='labour_list'),
    path('labour/add/', views.labour_create, name='labour_create'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('reports/project-cost/', views.project_cost_report,name='project_cost_report'),

]