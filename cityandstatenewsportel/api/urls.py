from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.register,              name='api_register'),
    path('auth/login/',    TokenObtainPairView.as_view(), name='api_login'),
    path('auth/refresh/',  TokenRefreshView.as_view(),   name='api_refresh'),
    path('auth/me/',       views.me,                    name='api_me'),

    # Articles
    path('articles/',          views.articles,       name='api_articles'),
    path('articles/trending/', views.trending,       name='api_trending'),
    path('articles/<int:pk>/', views.article_detail, name='api_article_detail'),

    # Article actions
    path('articles/<int:pk>/comments/', views.add_comment,     name='api_add_comment'),
    path('articles/<int:pk>/bookmark/', views.toggle_bookmark, name='api_bookmark'),

    # Meta
    path('categories/', views.categories, name='api_categories'),
    path('locations/',  views.locations,  name='api_locations'),
    path('search/',     views.search,     name='api_search'),
]
