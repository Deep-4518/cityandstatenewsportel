from rest_framework import serializers
from django.contrib.auth import get_user_model
from news.models import Article, ArticleMedia, Comment, Bookmark

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role',
                  'city', 'state', 'preferred_city', 'preferred_state', 'profile_photo']
        read_only_fields = ['id']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'role', 'gender', 'mobile']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ArticleMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleMedia
        fields = ['id', 'media_type', 'media_upload', 'media_url', 'uploaded_date']


class ArticleListSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    thumbnail   = serializers.SerializerMethodField()
    excerpt     = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'title', 'excerpt', 'category', 'city', 'state',
                  'author_name', 'thumbnail', 'views_count', 'is_published', 'created_at']

    def get_author_name(self, obj):
        return f"{obj.author.first_name or ''} {obj.author.last_name or ''}".strip() or obj.author.email

    def get_thumbnail(self, obj):
        media = obj.media.filter(media_type='Image').first()
        if not media:
            return None
        request = self.context.get('request')
        if media.media_upload and request:
            return request.build_absolute_uri(media.media_upload.url)
        return media.media_url

    def get_excerpt(self, obj):
        import re
        text = re.sub(r'<[^>]+>', '', obj.content)
        return (text[:160] + '…') if len(text) > 160 else text


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user_name', 'comment_text', 'comment_date']

    def get_user_name(self, obj):
        return obj.user.first_name or obj.user.email


class ArticleDetailSerializer(serializers.ModelSerializer):
    author   = UserSerializer(read_only=True)
    media    = ArticleMediaSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'category', 'city', 'state',
                  'author', 'media', 'comments', 'views_count', 'is_published',
                  'created_at', 'updated_at']

    def get_comments(self, obj):
        qs = obj.comment_set.filter(status='Visible').order_by('-comment_date')
        return CommentSerializer(qs, many=True).data


class ArticleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['title', 'content', 'category', 'city', 'state', 'is_published']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
