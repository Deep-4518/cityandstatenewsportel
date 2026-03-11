from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, SignupForm
from django.core.mail import send_mail
from django.conf import settings

# ✅ Home View
def home_view(request):
    return render(request, 'core/home.html')


# ✅ Dashboard (Only for Logged-in Users)
@login_required
def dashboard_view(request):
    if request.user.role == "owner":
        return redirect('owner_dashboard')
    return redirect('user_dashboard')


# ✅ Signup View
def signup_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    form = SignupForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            email = form.cleaned_data.get('email')
            
            # send_mail(
            #     subject="Welcome to City and State News Portal",
            #     message="Thank you for signing up!",
            #     from_email=settings.EMAIL_HOST_USER,
            #     recipient_list=[email],
            #     fail_silently=False
            # )
            
            login(request, user)

            messages.success(request, "Account created successfully!")

            if user.role == "owner":
                return redirect('owner_dashboard')
            return redirect('user_dashboard')

    return render(request, 'core/signup.html', {'form': form})


# ✅ Login View
def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')

            user = authenticate(
                request,
                username=email,   # email as username
                password=password
            )

            if user is not None:
                login(request, user)
                messages.success(request, "Login successful!")

                if user.role == "owner":
                    return redirect('owner_dashboard')
                return redirect('user_dashboard')

            else:
                messages.error(request, "Invalid email or password")

    return render(request, 'core/login.html', {'form': form})


# ✅ Logout View
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('login')