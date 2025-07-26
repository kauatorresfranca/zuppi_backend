from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from .models import Post, PostAction
import json

User = get_user_model()

def post_list(request):
    posts = Post.objects.all().order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count, 
             'created_at': post.created_at.isoformat()} 
            for post in posts]
    return JsonResponse({'posts': data})

@login_required
def post_create(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        if text:
            post = Post.objects.create(author=request.user, text=text)
            return JsonResponse({'id': post.id, 'text': post.text, 'author': request.user.username, 'created_at': post.created_at.isoformat()})
        return JsonResponse({'error': 'Texto ausente'}, status=400)
    return JsonResponse({'error': 'Método inválido'}, status=400)

@login_required
def post_actions(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    actions = PostAction.objects.filter(user=request.user, post=post).values('action_type')
    return JsonResponse({'actions': list(actions)})

@login_required
def post_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='like').first()
    if action:
        action.delete()
        post.likes_count = max(0, post.likes_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='like')
        post.likes_count += 1
    post.save()
    return JsonResponse({'likes_count': post.likes_count, 'id': post.id})

@login_required
def post_repost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='repost').first()
    if action:
        action.delete()
        post.reposts_count = max(0, post.reposts_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='repost')
        post.reposts_count += 1
    post.save()
    return JsonResponse({'reposts_count': post.reposts_count, 'id': post.id})

@login_required
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='comment').first()
    if action:
        action.delete()
        post.comments_count = max(0, post.comments_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='comment')
        post.comments_count += 1
    post.save()
    return JsonResponse({'comments_count': post.comments_count, 'id': post.id})

@login_required
def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='share').first()
    if action:
        action.delete()
        post.shares_count = max(0, post.shares_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='share')
        post.shares_count += 1
    post.save()
    return JsonResponse({'shares_count': post.shares_count, 'id': post.id})

@login_required
def feed_list(request):
    following_users = request.user.following.all()
    posts = Post.objects.filter(author__in=following_users).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count, 
             'created_at': post.created_at.isoformat()} 
            for post in posts]
    return JsonResponse({'posts': data})

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    if user_to_follow != request.user:
        if request.user.following.filter(id=user_id).exists():
            request.user.following.remove(user_to_follow)
        else:
            request.user.following.add(user_to_follow)
    return JsonResponse({'status': 'updated', 'following_count': request.user.following.count()})

def user_suggestions(request):
    users = User.objects.exclude(id=request.user.id).values('id', 'username') if request.user.is_authenticated else User.objects.all().values('id', 'username')[:5]
    return JsonResponse({'suggestions': list(users)})

@login_required
def profile(request):
    user = request.user
    profile_data = {
        'username': user.username,
        'handle': user.username.lower(),
        'bio': user.bio or '',
        'location': user.location or '',
        'profile_picture': user.profile_picture.url if user.profile_picture else '',
        'cover_image': user.cover_image.url if user.cover_image else '',
        'followers': user.followers_set.count(),
        'following': user.following.count(),
        'posts_count': user.posts.count(),
        'following': [user.id for user in user.following.all()]
    }
    return JsonResponse(profile_data)

@login_required
def profile_posts(request):
    posts = Post.objects.filter(author=request.user).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count, 
             'created_at': post.created_at.isoformat()} 
            for post in posts]
    return JsonResponse({'posts': data})

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'status': 'success', 'username': user.username})
        return JsonResponse({'error': 'Credenciais inválidas'}, status=401)
    return JsonResponse({'error': 'Método inválido'}, status=400)

@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Usuário já existe'}, status=400)
        user = User.objects.create_user(username=username, password=password, email=email)
        login(request, user)
        return JsonResponse({'status': 'success', 'username': user.username})
    return JsonResponse({'error': 'Método inválido'}, status=400)

def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Método inválido'}, status=400)

@csrf_exempt
@login_required
def profile_update(request):
    if request.method == 'PATCH':
        user = request.user
        try:
            bio = request.POST.get('bio', user.bio)
            location = request.POST.get('location', user.location)
            profile_picture = request.FILES.get('profile_picture', None)

            user.bio = bio
            user.location = location
            if profile_picture:
                user.profile_picture = profile_picture
            user.save()

            return JsonResponse({
                'status': 'success',
                'bio': user.bio,
                'location': user.location,
                'profile_picture': user.profile_picture.url if user.profile_picture else '',
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método inválido'}, status=400)