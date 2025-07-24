from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:post_id>/like/', views.post_like, name='post_like'),
    path('posts/<int:post_id>/repost/', views.post_repost, name='post_repost'),
    path('posts/<int:post_id>/comment/', views.post_comment, name='post_comment'),
    path('posts/<int:post_id>/share/', views.post_share, name='post_share'),
    path('feed/', views.feed_list, name='feed_list'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('suggestions/', views.user_suggestions, name='user_suggestions'),  # Correção aqui
]