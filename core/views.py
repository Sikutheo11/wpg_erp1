from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import get_user_modules



def home(request):

    return render(
        request,
        "core/home.html"
    )



@login_required
def customer_dashboard(request):

    return render(
        request,
        "accounts/customer_dashboard.html"
    )



@login_required
def dashboard(request):

    modules = get_user_modules(
        request.user
    )


    return render(request,"core/dashboard.html", {"modules": modules})