from django.urls import path
from .views import construction_dashboard

urlpatterns = [
    path(
        'dashboard/',
        construction_dashboard,
        name='construction_dashboard'
    ),
]