from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, F, Count, ExpressionWrapper, FloatField
from django.shortcuts import get_object_or_404

from news.models import Article, Comment, Bookmark
from .serializers import (
    ArticleListSerializer, ArticleDetailSerializer,
    ArticleWriteSerializer, CommentSerializer,
    RegisterSerializer, UserSerializer,
)


class ArticlePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


# ── Auth ───────────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


# ── Articles ───────────────────────────────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def articles(request):
    if request.method == 'GET':
        qs = Article.objects.prefetch_related('media').filter(is_published=True)
        q        = request.GET.get('q', '').strip()
        category = request.GET.get('category', '')
        city     = request.GET.get('city', '')
        state    = request.GET.get('state', '')
        sort     = request.GET.get('sort', '-created_at')

        if q:        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
        if category: qs = qs.filter(category__iexact=category)
        if city:     qs = qs.filter(city__iexact=city)
        if state:    qs = qs.filter(state__iexact=state)

        sort_map = {'latest':'-created_at','oldest':'created_at','views':'-views_count','az':'title'}
        qs = qs.order_by(sort_map.get(sort, '-created_at'))

        paginator = ArticlePagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ArticleListSerializer(page, many=True, context={'request': request}).data
        )

    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
    serializer = ArticleWriteSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if request.method == 'GET':
        Article.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
        return Response(ArticleDetailSerializer(article, context={'request': request}).data)

    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'PUT':
        serializer = ArticleWriteSerializer(article, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    article.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Trending ───────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def trending(request):
    qs = Article.objects.filter(is_published=True).annotate(
        score=ExpressionWrapper(
            F('views_count') * 0.5 + Count('comment') * 3,
            output_field=FloatField()
        )
    ).order_by('-score').prefetch_related('media')[:10]
    return Response(ArticleListSerializer(qs, many=True, context={'request': request}).data)


# ── Categories ─────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def categories(request):
    cats = (Article.objects.filter(is_published=True)
            .values_list('category', flat=True).distinct()
            .exclude(category__isnull=True).exclude(category='').order_by('category'))
    return Response(list(cats))


# ── Locations ──────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def locations(request):
    cities = list(Article.objects.values_list('city', flat=True)
                  .distinct().exclude(city__isnull=True).exclude(city='').order_by('city'))
    states = list(Article.objects.values_list('state', flat=True)
                  .distinct().exclude(state__isnull=True).exclude(state='').order_by('state'))
    return Response({'cities': cities, 'states': states})


# ── Comments ───────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, pk):
    article = get_object_or_404(Article, pk=pk)
    text = request.data.get('comment_text', '').strip()
    if not text:
        return Response({'detail': 'Comment text required.'}, status=status.HTTP_400_BAD_REQUEST)
    comment = Comment.objects.create(user=request.user, article=article, comment_text=text)
    return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


# ── Bookmarks ──────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_bookmark(request, pk):
    article = get_object_or_404(Article, pk=pk)
    bm, created = Bookmark.objects.get_or_create(user=request.user, article=article)
    if not created:
        bm.delete()
        return Response({'bookmarked': False})
    return Response({'bookmarked': True})


# ── Search ─────────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def search(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return Response({'count': 0, 'results': []})
    qs = Article.objects.filter(is_published=True).filter(
        Q(title__icontains=q) | Q(content__icontains=q) | Q(category__icontains=q)
    ).prefetch_related('media').order_by('-created_at')

    paginator = ArticlePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(
        ArticleListSerializer(page, many=True, context={'request': request}).data
    )
