from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('customer_dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('manager_dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),    
]