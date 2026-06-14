from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, login as auth_login
from .forms import LoginForm, UserForm, UserProfileForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import UserProfile

def registerUser(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
       
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            #  create empty profile
            UserProfile.objects.create(user=user)

            # login automatically
            login(request, user)

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

            user = authenticate(request, username=username, password=password)

            if user is not None:
                auth_login(request, user)
                if user is not None:
                    auth_login(request, user)
                    if user.role == 'customer':
                        return redirect('customer_dashboard')

                    elif user.role == 'worker':
                        return redirect('worker_dashboard')

                    elif user.role == 'manager':
                        return redirect('manager_dashboard')

                    elif user.role == 'admin':
                        return redirect('admin_dashboard')

    return render(request, 'accounts/login.html', {'form': form})


def logout(request):
    logout(request)
    return redirect('login')



@login_required
def profile(request):
    profile = request.user.userprofile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            form.save()
            return redirect('profile')

    else:

        form = UserProfileForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
    }

    return render(request,'accounts/profile.html', context)

def password_reset(request):
    return render(request, 'accounts/admin_dashboard.html')