from django.shortcuts import render

def owner_dashboard(request):
    return render(request, 'owner_dashboard.html')

from .models import Article

def user_dashboard(request):
    # Fetching real articles or placeholders depending on DB state
    latest_news = Article.objects.order_by('-created_at')[:4]
    trending_news = Article.objects.order_by('-views_count')[:4]
    
    # Simulating Local & Recommended News based on User preferences
    local_news = []
    recommended_news = []
    
    if request.user.is_authenticated:
        if request.user.preferred_city:
            local_news = Article.objects.filter(city=request.user.preferred_city)[:4]
        elif request.user.city:
            local_news = Article.objects.filter(city=request.user.city)[:4]
            
        # Basic recommendation simulation (can be expanded later)
        recommended_news = Article.objects.filter(views_count__gte=5).order_by('?')[:4]

    context = {
        'latest_news': latest_news,
        'trending_news': trending_news,
        'local_news': local_news,
        'recommended_news': recommended_news,
    }
    return render(request, 'user_dashboard.html', context)

def add_article(request):
    # This view will just return the add_article template for now.
    return render(request, 'add_article.html')

from .forms import PaymentForm

def add_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Process the payment logic here
            pass # Currently just displaying the form based on user request
    else:
        form = PaymentForm()
    
    return render(request, 'add_payment.html', {'form': form})

def manage_articles(request):
    articles = Article.objects.all().order_by('-created_at')
    return render(request, 'manage_articles.html', {'articles': articles})

def analytics(request):
    total_views = sum(article.views_count for article in Article.objects.all())
    total_articles = Article.objects.count()
    avg_views = total_views // total_articles if total_articles > 0 else 0
    top_articles = Article.objects.order_by('-views_count')[:5]
    
    context = {
        'total_views': total_views,
        'total_articles': total_articles,
        'avg_views': avg_views,
        'top_articles': top_articles,
    }
    return render(request, 'analytics.html', context)