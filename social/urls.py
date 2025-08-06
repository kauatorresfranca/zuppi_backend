from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostList.as_view(), name='post_list'),
    path('posts/create/', views.PostCreate.as_view(), name='post_create'),
    path('posts/<int:post_id>/like/', views.PostLike.as_view(), name='post_like'),
    path('posts/<int:post_id>/repost/', views.PostRepost.as_view(), name='post_repost'),
    path('posts/<int:post_id>/comment/', views.PostComment.as_view(), name='post_comment'),
    path('posts/<int:post_id>/comments/', views.PostCommentsList.as_view(), name='post_comments_list'),
    path('posts/<int:post_id>/share/', views.PostShare.as_view(), name='post_share'),
    path('posts/<int:post_id>/actions/', views.PostActions.as_view(), name='post_actions'),
    path('feed/', views.FeedList.as_view(), name='feed_list'),
    path('follow/<int:user_id>/', views.FollowUser.as_view(), name='follow_user'),
    path('suggestions/', views.UserSuggestions.as_view(), name='user_suggestions'),
    path('profile/', views.Profile.as_view(), name='profile'),
    path('profile/posts/', views.ProfilePosts.as_view(), name='profile_posts'),
    path('profile/update/', views.ProfileUpdate.as_view(), name='profile_update'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]