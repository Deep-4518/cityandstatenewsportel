from django.urls import path
from .views import owner_dashboard, user_dashboard, add_article

urlpatterns = [
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('user/', user_dashboard, name='user_dashboard'),
    path('add-article/', add_article, name='add_article'),
]