from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:post_id>/like/', views.post_like, name='post_like'),
    path('posts/<int:post_id>/repost/', views.post_repost, name='post_repost'),
    path('posts/<int:post_id>/comment/', views.post_comment, name='post_comment'),
    path('posts/<int:post_id>/share/', views.post_share, name='post_share'),
    path('posts/<int:post_id>/actions/', views.post_actions, name='post_actions'),
    path('feed/', views.feed_list, name='feed_list'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('suggestions/', views.user_suggestions, name='user_suggestions'),
    path('profile/', views.profile, name='profile'),
    path('profile/posts/', views.profile_posts, name='profile_posts'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('get_csrf_token/', views.get_csrf_token, name='get_csrf_token'),
    path('logout/', views.logout_view, name='logout'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)