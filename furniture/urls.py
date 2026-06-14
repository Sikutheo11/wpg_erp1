from django.urls import path
from . import views

urlpatterns = [
    path('furniture_dashboard/', views.furniture_dashboard, name='furniture_dashboard'),
      
]