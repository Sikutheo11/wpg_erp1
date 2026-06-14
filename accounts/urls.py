from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('registerUser/', views.registerUser, name='registerUser'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'
    ), name='password_reset'),
    path('profile/', views.profile, name='profile'),
       
]