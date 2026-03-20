from django.urls import path
from .views import (owner_dashboard, user_dashboard, add_article, add_payment,
                    manage_articles, delete_article, analytics, admin_analytics_dashboard,
                    report_fake_news, bookmark_article, reader_search)

urlpatterns = [
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('user/', user_dashboard, name='user_dashboard'),
    path('add-article/', add_article, name='add_article'),
    path('add-payment/', add_payment, name='add_payment'),
    path('manage-articles/', manage_articles, name='manage_articles'),
    path('delete-article/<int:article_id>/', delete_article, name='delete_article'),
    path('analytics/', analytics, name='analytics'),
    path('admin-analytics/', admin_analytics_dashboard, name='admin_analytics'),
    path('report-fake-news/<int:article_id>/', report_fake_news, name='report_fake_news'),
    path('bookmark/<int:article_id>/', bookmark_article, name='bookmark_article'),
    path('search/', reader_search, name='reader_search'),
]