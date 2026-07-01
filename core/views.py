from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .dashboard import get_dashboard_context



def home(request):
    return render(request, "core/home.html" )

@login_required
def customer_dashboard(request):
    return render(request, "accounts/customer_dashboard.html")




@login_required
def dashboard(request):

    context = get_dashboard_context(
        request.user
    )

    return render( request,  "core/dashboard.html", context)

