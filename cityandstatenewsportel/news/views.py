from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Count, Q, ExpressionWrapper, FloatField, Sum
from core.models import User
from .models import Article, FakeNewsReport, AdPayment, Reaction, Comment, Bookmark

def owner_dashboard(request):
    return render(request, 'owner_dashboard.html')

def user_dashboard(request):
    # Fetching real articles or placeholders depending on DB state
    latest_news = Article.objects.order_by('-created_at')[:4]
    # Trending Algorithm: Views * 0.5 + Likes * 2 + Comments * 3
    trending_news = Article.objects.annotate(
        trending_score=ExpressionWrapper(
            F('views_count') * 0.5 + 
            Count('reaction', filter=Q(reaction__reaction_type='Like')) * 2.0 + 
            Count('comment') * 3.0,
            output_field=FloatField()
        )
    ).order_by('-trending_score')[:10]
    
    local_news = []
    recommended_news = []
    
    if request.user.is_authenticated:
        query = Q()
        if request.user.preferred_city:
            query |= Q(city__icontains=request.user.preferred_city)
        if request.user.preferred_state:
            query |= Q(state__icontains=request.user.preferred_state)
        elif request.user.city:
            query |= Q(city__icontains=request.user.city)
        
        if query:
            local_news = Article.objects.filter(query).order_by('-created_at')[:4]
            
        # Basic recommendation simulation
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

def admin_analytics_dashboard(request):
    total_articles = Article.objects.count()
    total_users = User.objects.count()
    total_comments = Comment.objects.count()
    total_reactions = Reaction.objects.count()
    
    active_ads = AdPayment.objects.filter(status='Completed').count()
    revenue_dict = AdPayment.objects.filter(status='Completed').aggregate(total_rev=Sum('amount'))
    total_revenue = revenue_dict['total_rev'] or 0

    context = {
        'total_articles': total_articles,
        'total_users': total_users,
        'total_comments': total_comments,
        'total_reactions': total_reactions,
        'active_ads': active_ads,
        'total_revenue': total_revenue,
    }
    return render(request, 'admin_analytics.html', context)

@login_required
def report_fake_news(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        if reason:
            FakeNewsReport.objects.create(
                user=request.user,
                article=article,
                reason=reason
            )
            messages.success(request, 'Thank you for your report. It has been submitted for review.')
            return redirect('user_dashboard')
    return render(request, 'report_fake_news.html', {'article': article})

@login_required
def bookmark_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, article=article)
    if not created:
        bookmark.delete()
        messages.success(request, 'Article removed from bookmarks.')
    else:
        messages.success(request, 'Article bookmarked successfully.')
    return redirect('user_dashboard')