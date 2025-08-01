from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from .models import Post, PostAction
import json
import logging
from django.views.decorators.cache import never_cache
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.exceptions import ParseError
from io import BytesIO

logger = logging.getLogger(__name__)

User = get_user_model()

def post_list(request):
    """
    Retorna a lista de todos os posts. Acessível publicamente.
    """
    posts = Post.objects.all().order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count,
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count,
             'created_at': post.created_at.isoformat()}
            for post in posts]
    return JsonResponse({'posts': data})

def post_create(request):
    """
    Cria um novo post. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text')
            if text:
                post = Post.objects.create(author=request.user, text=text)
                logger.debug(f"Post criado: id={post.id}, autor={request.user.username}")
                return JsonResponse({'id': post.id, 'text': post.text, 'author': request.user.username, 'created_at': post.created_at.isoformat()})
            return JsonResponse({'error': 'Texto ausente'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
    return JsonResponse({'error': 'Método inválido'}, status=400)

def post_actions(request, post_id):
    """
    Retorna as ações do usuário em um post. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    post = get_object_or_404(Post, id=post_id)
    actions = PostAction.objects.filter(user=request.user, post=post).values('action_type')
    logger.debug(f"Ações do post {post_id}: {list(actions)}")
    return JsonResponse({'actions': list(actions)})

def post_like(request, post_id):
    """
    Adiciona ou remove um "like" de um post. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='like').first()
    if action:
        action.delete()
        post.likes_count = max(0, post.likes_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='like')
        post.likes_count += 1
    post.save()
    logger.debug(f"Like atualizado no post {post_id}: likes_count={post.likes_count}")
    return JsonResponse({'likes_count': post.likes_count, 'id': post.id})

def post_repost(request, post_id):
    """
    Adiciona ou remove um "repost" de um post. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='repost').first()
    if action:
        action.delete()
        post.reposts_count = max(0, post.reposts_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='repost')
        post.reposts_count += 1
    post.save()
    logger.debug(f"Repost atualizado no post {post_id}: reposts_count={post.reposts_count}")
    return JsonResponse({'reposts_count': post.reposts_count, 'id': post.id})

def post_comment(request, post_id):
    """
    Adiciona ou remove um "comentário" de um post. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='comment').first()
    if action:
        action.delete()
        post.comments_count = max(0, post.comments_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='comment')
        post.comments_count += 1
    post.save()
    logger.debug(f"Comentário atualizado no post {post_id}: comments_count={post.comments_count}")
    return JsonResponse({'comments_count': post.comments_count, 'id': post.id})

def post_share(request, post_id):
    """
    Adiciona ou remove um "compartilhamento" de um post. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    post = get_object_or_404(Post, id=post_id)
    action = PostAction.objects.filter(user=request.user, post=post, action_type='share').first()
    if action:
        action.delete()
        post.shares_count = max(0, post.shares_count - 1)
    else:
        PostAction.objects.create(user=request.user, post=post, action_type='share')
        post.shares_count += 1
    post.save()
    logger.debug(f"Compartilhamento atualizado no post {post_id}: shares_count={post.shares_count}")
    return JsonResponse({'shares_count': post.shares_count, 'id': post.id})

def feed_list(request):
    """
    Retorna o feed de posts dos usuários que o usuário logado segue. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    following_users = request.user.following.all()
    posts = Post.objects.filter(author__in=following_users).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count,
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count,
             'created_at': post.created_at.isoformat()}
            for post in posts]
    logger.debug(f"Feed response: {{'posts': {data}}}")
    return JsonResponse({'posts': data})

def follow_user(request, user_id):
    """
    Segue ou deixa de seguir um usuário. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    user_to_follow = get_object_or_404(User, id=user_id)
    if user_to_follow != request.user:
        if request.user.following.filter(id=user_id).exists():
            request.user.following.remove(user_to_follow)
        else:
            request.user.following.add(user_to_follow)
    logger.debug(f"Follow atualizado: user={request.user.username}, target={user_to_follow.username}")
    return JsonResponse({'status': 'updated', 'following_count': request.user.following.count()})

def user_suggestions(request):
    """
    Retorna sugestões de usuários para seguir. Acessível publicamente.
    """
    users = User.objects.exclude(id=request.user.id).values('id', 'username') if request.user.is_authenticated else User.objects.all().values('id', 'username')[:5]
    return JsonResponse({'suggestions': list(users)})

def profile(request):
    """
    Retorna os dados do perfil do usuário logado. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

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
    logger.debug(f"Profile response: {profile_data}")
    return JsonResponse(profile_data)

def profile_posts(request):
    """
    Retorna os posts do usuário logado. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    posts = Post.objects.filter(author=request.user).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count,
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count,
             'created_at': post.created_at.isoformat()}
            for post in posts]
    logger.debug(f"Profile posts response: {{'posts': {data}}}")
    return JsonResponse({'posts': data})

def login_view(request):
    """
    Gerencia o login do usuário.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.debug(f"Login bem-sucedido: {username}")
            return JsonResponse({'status': 'success', 'username': user.username})
        logger.warning(f"Login falhou: {username}")
        return JsonResponse({'error': 'Credenciais inválidas'}, status=401)
    return JsonResponse({'error': 'Método inválido'}, status=400)

def register_view(request):
    """
    Gerencia o registro de novos usuários.
    """
    if request.method == 'POST':
        logger.debug(f"Recebendo requisição POST para registro. Corpo bruto: {request.body.decode('utf-8')}")
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            logger.debug(f"JSON parseado: username={username}, password={'*' * len(password) if password else 'None'}, email={email}")
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON na requisição de registro: {e}")
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        if not username or not password or not email:
            return JsonResponse({'error': 'Todos os campos são obrigatórios.'}, status=400)

        if User.objects.filter(username=username).exists():
            logger.warning(f"Registro falhou: usuário {username} já existe")
            return JsonResponse({'error': 'Usuário já existe'}, status=400)

        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            login(request, user)
            logger.debug(f"Registro bem-sucedido: {username}")
            return JsonResponse({'status': 'success', 'username': user.username})
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            return JsonResponse({'error': 'Falha ao criar usuário.'}, status=500)
    return JsonResponse({'error': 'Método inválido'}, status=400)

@never_cache
def get_csrf_token(request):
    """
    Retorna o token CSRF e define o cookie csrftoken.
    """
    token = get_token(request)
    response = JsonResponse({'csrfToken': token})
    response.set_cookie(
        'csrftoken',
        token,
        max_age=31449600,
        secure=True,
        httponly=False,
        samesite='None'
    )
    logger.debug(f"CSRF token gerado e cookie definido: {token}")
    return response

def logout_view(request):
    """
    Gerencia o logout do usuário. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)
        
    if request.method == 'POST':
        logout(request)
        logger.debug("Logout bem-sucedido")
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Método inválido'}, status=400)

def profile_update(request):
    """
    Atualiza o perfil do usuário. Requer autenticação.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)

    if request.method == 'PATCH':
        user = request.user
        try:
            raw_body = request.body
            logger.debug(f"Request headers: {dict(request.headers)}")
            logger.debug(f"Content-Type: {request.content_type}")
            logger.debug(f"Raw request body length: {len(raw_body)}")
            logger.debug(f"Raw request body: {raw_body.decode('utf-8', errors='ignore')}")

            data = None
            files = None

            if request.content_type.startswith('multipart/form-data'):
                try:
                    if hasattr(request, '_read_started'):
                        request._read_started = False
                    if hasattr(request, '_stream'):
                        request._stream.seek(0)
                    else:
                        request._stream = BytesIO(raw_body)
                        request.read = request._stream.read

                    drf_request = Request(request, parsers=[MultiPartParser()])
                    data = drf_request.data
                    files = drf_request.FILES

                except ParseError as e:
                    logger.error(f"Erro de parsing de multipart/form-data com DRF MultiPartParser: {e}")
                    return JsonResponse({'error': f'Falha ao processar dados de formulário: {e}'}, status=400)
                except Exception as e:
                    logger.error(f"Erro inesperado ao usar DRF MultiPartParser: {e.__class__.__name__}: {e}")
                    return JsonResponse({'error': f'Erro inesperado no parsing: {e}'}, status=400)

                bio = data.get('bio', user.bio or '')
                username = data.get('username')
                profile_picture = files.get('profile_picture')
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                remove_profile_picture = data.get('remove_profile_picture', 'false').lower() == 'true'

                logger.debug(f"Dados parseados (multipart): POST={dict(data)}, FILES={dict(files)}")

            elif request.content_type.startswith('application/json'):
                data_json = json.loads(raw_body)
                bio = data_json.get('bio', user.bio or '')
                username = data_json.get('username')
                old_password = data_json.get('old_password')
                new_password = data_json.get('new_password')
                profile_picture = None
                remove_profile_picture = data_json.get('remove_profile_picture', False)
                logger.debug(f"Dados parseados (JSON): {data_json}")
            else:
                logger.warning(f"Tipo de conteúdo inesperado para PATCH: {request.content_type}")
                return JsonResponse({'error': 'Tipo de conteúdo não suportado para esta operação.'}, status=415)

            logger.debug(f"Dados processados: username={username!r}, profile_picture={profile_picture}, bio={bio!r}, old_password={old_password!r}, new_password={new_password!r}, remove_profile_picture={remove_profile_picture}")

            if not username:
                logger.warning("Username vazio ou não fornecido")
                return JsonResponse({'error': 'Nome de usuário é obrigatório'}, status=400)
            if len(username) < 3:
                logger.warning(f"Username muito curto: {username}")
                return JsonResponse({'error': 'O nome de usuário deve ter pelo menos 3 caracteres'}, status=400)
            if username != user.username and User.objects.filter(username=username).exists():
                logger.warning(f"Username já existe: {username}")
                return JsonResponse({'error': 'Nome de usuário já existe'}, status=400)

            if new_password:
                if not old_password or not authenticate(request, username=user.username, password=old_password):
                    logger.warning("Senha antiga inválida")
                    return JsonResponse({'error': 'Senha antiga inválida'}, status=400)
                user.set_password(new_password)

            user.username = username
            user.bio = bio
            if profile_picture:
                user.profile_picture = profile_picture
            elif remove_profile_picture:
                user.profile_picture = None
            user.save()

            logger.debug(f"Salvo: username={user.username}, profile_picture={user.profile_picture.url if user.profile_picture else ''}")

            return JsonResponse({
                'status': 'success',
                'username': user.username,
                'bio': user.bio or '',
                'location': user.location or '',
                'profile_picture': user.profile_picture.url if user.profile_picture else '',
            })
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil: {e.__class__.__name__}: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método inválido'}, status=400)