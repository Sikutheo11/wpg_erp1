from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import LoginForm, UserForm, UserProfileForm
from .models import User
from .utils import redirect_by_role

def registerUser(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
       
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()

                customer_group, unused_created = Group.objects.get_or_create(
                    name="Customer"
                )
                user.groups.add(customer_group)

            auth_login(request, user)

            return redirect('profile')

    else:
        form = UserForm()
    context = {
        'form':form,
    }
    return render(request, 'accounts/registerUser.html',context )

def login(request):
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            email = (
                User.objects.filter(username=identifier)
                .values_list("email", flat=True)
                .first()
                or identifier
            )
            user = authenticate(
                request,
                username=email,
                password=password
            )
            if user is not None:
                auth_login(request, user)

                return redirect_by_role(user)
            form.add_error(
                None,
                "The email/username or password is incorrect.",
            )
    return render(request,'accounts/login.html',{'form':form})


@require_POST
def logout(request):
    auth_logout(request)
    return redirect('login')

@login_required
def profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect_by_role(request.user)
    else:

        form = UserProfileForm(instance=profile)
    return render(request,'accounts/profile.html',{
            'form':form,
            'profile':profile
        }
    )

def password_reset(request):
    return render(request, 'accounts/admin_dashboard.html')
