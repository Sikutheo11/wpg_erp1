from django.urls import path
from .import views

urlpatterns = [
    path('construction_dashboard/', views.construction_dashboard, name='construction_dashboard'),
]