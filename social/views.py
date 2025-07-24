from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Post, PostAction
from django.http import JsonResponse
import json

User = get_user_model()

@login_required
def post_list(request):
    posts = Post.objects.all().order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count} 
            for post in posts]
    return JsonResponse({'posts': data})

@login_required
def post_create(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        if text:
            post = Post.objects.create(author=request.user, text=text)
            return JsonResponse({'id': post.id, 'text': post.text, 'author': post.author.username})
    return JsonResponse({'error': 'Método inválido ou texto ausente'}, status=400)

@login_required
def post_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action, created = PostAction.objects.get_or_create(user=request.user, post=post, action_type='like')
    if created:
        post.likes_count += 1
        post.save()
    return JsonResponse({'likes_count': post.likes_count})

@login_required
def post_repost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action, created = PostAction.objects.get_or_create(user=request.user, post=post, action_type='repost')
    if created:
        post.reposts_count += 1
        post.save()
    return JsonResponse({'reposts_count': post.reposts_count})

@login_required
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action, created = PostAction.objects.get_or_create(user=request.user, post=post, action_type='comment')
    if created:
        post.comments_count += 1
        post.save()
    return JsonResponse({'comments_count': post.comments_count})

@login_required
def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action, created = PostAction.objects.get_or_create(user=request.user, post=post, action_type='share')
    if created:
        post.shares_count += 1
        post.save()
    return JsonResponse({'shares_count': post.shares_count})

@login_required
def feed_list(request):
    following_users = request.user.following.all()
    posts = Post.objects.filter(author__in=following_users).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count} 
            for post in posts]
    return JsonResponse({'posts': data})

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    if user_to_follow != request.user:
        request.user.following.add(user_to_follow)
    return JsonResponse({'status': 'followed', 'following_count': request.user.following.count()})

@login_required
def user_suggestions(request):
    users = User.objects.exclude(id=request.user.id).values('id', 'username')
    return JsonResponse({'suggestions': list(users)})