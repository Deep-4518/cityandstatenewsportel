from django.shortcuts import render

def owner_dashboard(request):
    return render(request, 'owner_dashboard.html')

def user_dashboard(request):
    return render(request, 'user_dashboard.html')

def add_article(request):
    # This view will just return the add_article template for now.
    return render(request, 'add_article.html')