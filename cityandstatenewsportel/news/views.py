from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Count, Q, ExpressionWrapper, FloatField, Sum
from django.http import JsonResponse
from core.models import User
from .models import Article, FakeNewsReport, AdPayment, Reaction, Comment, Bookmark, ReadingHistory

def owner_dashboard(request):
    return render(request, 'owner_dashboard.html')

def user_dashboard(request):
    latest_news = Article.objects.order_by('-created_at')[:6]
    trending_news = Article.objects.annotate(
        trending_score=ExpressionWrapper(
            F('views_count') * 0.5 +
            Count('reaction', filter=Q(reaction__reaction_type='Like')) * 2.0 +
            Count('comment') * 3.0,
            output_field=FloatField()
        )
    ).order_by('-trending_score')[:8]

    local_news = []
    state_news = []
    recommended_news = []
    saved_articles = []
    reading_history = []
    saved_count = 0
    comments_count = 0
    articles_read_count = 0
    bookmarked_ids = set()

    if request.user.is_authenticated:
        # City news
        city_q = Q()
        if request.user.preferred_city:
            city_q |= Q(city__icontains=request.user.preferred_city)
        elif request.user.city:
            city_q |= Q(city__icontains=request.user.city)
        if city_q:
            local_news = Article.objects.filter(city_q).order_by('-created_at')[:4]

        # State news
        state_q = Q()
        if request.user.preferred_state:
            state_q |= Q(state__icontains=request.user.preferred_state)
        elif request.user.state:
            state_q |= Q(state__icontains=request.user.state)
        if state_q:
            state_news = Article.objects.filter(state_q).order_by('-created_at')[:4]

        # Recommendations based on reading history categories
        read_categories = ReadingHistory.objects.filter(user=request.user).values_list('article__category', flat=True)
        if read_categories:
            recommended_news = Article.objects.filter(category__in=read_categories).exclude(
                id__in=ReadingHistory.objects.filter(user=request.user).values_list('article_id', flat=True)
            ).order_by('-views_count')[:4]
        if not recommended_news:
            recommended_news = Article.objects.filter(views_count__gte=1).order_by('-views_count')[:4]

        saved_articles = Bookmark.objects.filter(user=request.user).select_related('article').order_by('-created_at')[:5]
        saved_count = Bookmark.objects.filter(user=request.user).count()
        comments_count = Comment.objects.filter(user=request.user).count()
        reading_history = ReadingHistory.objects.filter(user=request.user).select_related('article')[:5]
        articles_read_count = ReadingHistory.objects.filter(user=request.user).count()
        bookmarked_ids = set(Bookmark.objects.filter(user=request.user).values_list('article_id', flat=True))

    categories = Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True)

    context = {
        'latest_news': latest_news,
        'trending_news': trending_news,
        'local_news': local_news,
        'state_news': state_news,
        'recommended_news': recommended_news,
        'saved_articles': saved_articles,
        'reading_history': reading_history,
        'saved_count': saved_count,
        'comments_count': comments_count,
        'articles_read_count': articles_read_count,
        'bookmarked_ids': bookmarked_ids,
        'categories': categories,
    }
    return render(request, 'user_dashboard.html', context)


def reader_search(request):
    """AJAX endpoint for search + filter in reader panel."""
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    date_filter = request.GET.get('date', '')
    city = request.GET.get('city', '')

    from django.utils import timezone
    import datetime

    articles = Article.objects.all()

    if q:
        articles = articles.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if category:
        articles = articles.filter(category__icontains=category)
    if city:
        articles = articles.filter(Q(city__icontains=city) | Q(state__icontains=city))
    if date_filter == 'today':
        articles = articles.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        articles = articles.filter(created_at__gte=timezone.now() - datetime.timedelta(days=7))
    elif date_filter == 'month':
        articles = articles.filter(created_at__gte=timezone.now() - datetime.timedelta(days=30))

    articles = articles.order_by('-created_at')[:12]

    data = []
    for a in articles:
        data.append({
            'id': a.id,
            'title': a.title,
            'category': a.category or 'General',
            'city': a.city or '',
            'state': a.state or '',
            'views_count': a.views_count,
            'created_at': a.created_at.strftime('%b %d, %Y'),
            'excerpt': a.content[:120] + '...' if len(a.content) > 120 else a.content,
        })
    return JsonResponse({'articles': data})

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
    from django.core.paginator import Paginator

    qs = Article.objects.select_related('author').prefetch_related('media').all()

    # Filters
    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status   = request.GET.get('status', '')
    sort     = request.GET.get('sort', '-created_at')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if category:
        qs = qs.filter(category__icontains=category)
    # Article model has no status field yet — treat views_count==0 as Draft proxy
    if status == 'published':
        qs = qs.filter(views_count__gt=0)
    elif status == 'draft':
        qs = qs.filter(views_count=0)

    sort_map = {
        'latest': '-created_at',
        'oldest': 'created_at',
        'views': '-views_count',
        'az': 'title',
    }
    qs = qs.order_by(sort_map.get(sort, '-created_at'))

    total_articles  = Article.objects.count()
    total_views     = Article.objects.aggregate(tv=Sum('views_count'))['tv'] or 0
    published_count = Article.objects.filter(views_count__gt=0).count()
    draft_count     = Article.objects.filter(views_count=0).count()
    categories      = Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True)

    paginator   = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    # trending threshold: top 20% by views
    trending_threshold = 10

    context = {
        'page_obj':          page_obj,
        'articles':          page_obj,          # alias for template
        'total_articles':    total_articles,
        'total_views':       total_views,
        'published_count':   published_count,
        'draft_count':       draft_count,
        'categories':        categories,
        'trending_threshold': trending_threshold,
        'q':        q,
        'category': category,
        'status':   status,
        'sort':     sort,
    }
    return render(request, 'manage_articles.html', context)

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
def delete_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Article deleted successfully.')
    return redirect('manage_articles')


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