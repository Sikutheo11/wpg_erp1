from django.shortcuts import render, redirect
from django.contrib.auth import authenticate,logout, login as auth_login
from .forms import LoginForm, UserForm, UserProfileForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import UserProfile
from .utils import redirect_by_role

def registerUser(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
       
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # login automatically
            login(request)

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
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(
                request,
                username=username,
                password=password
            )
            if user is not None:
                auth_login(request, user)

                return redirect(redirect_by_role(user))
    return render(request,'accounts/login.html',{'form':form})


def logout(request):

    if request.method == "POST":
        logout(request)

    return redirect('login')

@login_required
def profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect(redirect_by_role(request.user))
    else:

        form = UserProfileForm(instance=profile)
    return render(request,'accounts/profile.html',{
            'form':form,
            'profile':profile
        }
    )

def password_reset(request):
    return render(request, 'accounts/admin_dashboard.html')