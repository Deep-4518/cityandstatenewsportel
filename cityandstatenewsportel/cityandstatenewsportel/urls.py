from django.contrib import admin
from django.urls import path, include
from core.views import signup_view, login_view, home_view, dashboard_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication URLs
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Home & Dashboard
    path('', home_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # News App URLs
    path('news/', include('news.urls')),
]