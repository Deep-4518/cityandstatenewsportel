from django.urls import path
from .views import owner_dashboard, user_dashboard, add_article, add_payment, manage_articles, analytics

urlpatterns = [
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('user/', user_dashboard, name='user_dashboard'),
    path('add-article/', add_article, name='add_article'),
    path('add-payment/', add_payment, name='add_payment'),
    path('manage-articles/', manage_articles, name='manage_articles'),
    path('analytics/', analytics, name='analytics'),
]