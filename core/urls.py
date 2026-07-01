from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path('', views.home, name='home'),
    path('customer_dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

]