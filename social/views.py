from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from .models import Post, PostAction
import json
import logging

# NÃO precisamos mais do MultiPartParser do DRF para esta abordagem em views de função
# from rest_framework.parsers import MultiPartParser 
from django.http.request import QueryDict # Ainda útil para forçar o carregamento do POST/FILES

logger = logging.getLogger(__name__)

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
            logger.debug(f"Post criado: id={post.id}, autor={request.user.username}")
            return JsonResponse({'id': post.id, 'text': post.text, 'author': request.user.username, 'created_at': post.created_at.isoformat()})
        return JsonResponse({'error': 'Texto ausente'}, status=400)
    return JsonResponse({'error': 'Método inválido'}, status=400)

@login_required
def post_actions(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    actions = PostAction.objects.filter(user=request.user, post=post).values('action_type')
    logger.debug(f"Ações do post {post_id}: {list(actions)}")
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
    logger.debug(f"Like atualizado no post {post_id}: likes_count={post.likes_count}")
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
    logger.debug(f"Repost atualizado no post {post_id}: reposts_count={post.reposts_count}")
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
    logger.debug(f"Comentário atualizado no post {post_id}: comments_count={post.comments_count}")
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
    logger.debug(f"Compartilhamento atualizado no post {post_id}: shares_count={post.shares_count}")
    return JsonResponse({'shares_count': post.shares_count, 'id': post.id})

@login_required
def feed_list(request):
    following_users = request.user.following.all()
    posts = Post.objects.filter(author__in=following_users).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count, 
             'created_at': post.created_at.isoformat()} 
            for post in posts]
    logger.debug(f"Feed response: {{'posts': {data}}}")
    return JsonResponse({'posts': data})

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    if user_to_follow != request.user:
        if request.user.following.filter(id=user_id).exists():
            request.user.following.remove(user_to_follow)
        else:
            request.user.following.add(user_to_follow)
    logger.debug(f"Follow atualizado: user={request.user.username}, target={user_to_follow.username}")
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
    logger.debug(f"Profile response: {profile_data}")
    return JsonResponse(profile_data)

@login_required
def profile_posts(request):
    posts = Post.objects.filter(author=request.user).order_by('-created_at')
    data = [{'id': post.id, 'text': post.text, 'author': post.author.username, 'likes_count': post.likes_count, 
             'reposts_count': post.reposts_count, 'comments_count': post.comments_count, 'shares_count': post.shares_count, 
             'created_at': post.created_at.isoformat()} 
            for post in posts]
    logger.debug(f"Profile posts response: {{'posts': {data}}}")
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
            logger.debug(f"Login bem-sucedido: {username}")
            return JsonResponse({'status': 'success', 'username': user.username})
        logger.warning(f"Login falhou: {username}")
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
            logger.warning(f"Registro falhou: usuário {username} já existe")
            return JsonResponse({'error': 'Usuário já existe'}, status=400)
        user = User.objects.create_user(username=username, password=password, email=email)
        login(request, user)
        logger.debug(f"Registro bem-sucedido: {username}")
        return JsonResponse({'status': 'success', 'username': user.username})
    return JsonResponse({'error': 'Método inválido'}, status=400)

def get_csrf_token(request):
    token = get_token(request)
    logger.debug(f"CSRF token gerado: {token}")
    return JsonResponse({'csrfToken': token})

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        logger.debug("Logout bem-sucedido")
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Método inválido'}, status=400)

@csrf_exempt
@login_required
def profile_update(request):
    if request.method == 'PATCH':
        user = request.user
        try:
            logger.debug(f"Request headers: {dict(request.headers)}")
            logger.debug(f"Content-Type: {request.content_type}")
            logger.debug(f"Raw request body length: {len(request.body)}")
            logger.debug(f"Raw request body: {request.body}")

            # --- NOVA CORREÇÃO AQUI para lidar com PATCH de multipart/form-data em views de função ---
            if request.content_type.startswith('multipart/form-data'):
                # O Django não preenche request.POST e request.FILES para PATCH automaticamente.
                # Vamos fazer isso manualmente.
                # Criamos um QueryDict mutável a partir do corpo da requisição.
                # Note: Isso é mais complexo que simplesmente decodificar, pois precisa lidar
                # com as partes do multipart e potencialmente decodificar arquivos.
                # A forma mais confiável em uma view de função é usar a lógica que o Django usaria
                # se fosse um POST, ou reverter para uma abordagem mais "low-level" de parseamento
                # do multipart, sem o DRF MultiPartParser.

                # A solução mais "Django-idiomatic" para isso é usar um parser
                # que entenda como o Django lida com requisições POST com FormData.
                # Podemos simular isso forçando o Django a ler o corpo como se fosse POST.
                # Isso geralmente é feito através de middleware ou de parsers do DRF.
                # Como não estamos em DRF APIView, vamos simular o parsing o mais próximo possível.
                
                # Para evitar conflitos e o erro 'request', vamos usar a funcionalidade
                # interna do Django que popula request.POST e request.FILES a partir do corpo
                # da requisição, que geralmente é ativada para POST/PUT. Para PATCH, precisamos
                # de um truque: modificar o método da requisição temporariamente.

                # É um hack, mas funciona para forçar o Django a popular request.POST e request.FILES
                # Se o request.method fosse POST ou PUT, o Django faria isso automaticamente.
                original_method = request.method
                request.method = 'POST' # Temporariamente define como POST para forçar o parsing
                
                # Chama a função _load_post_and_files que preenche request.POST e request.FILES
                # Isso pode falhar se o corpo da requisição já foi lido.
                try:
                    request._load_post_and_files()
                except AttributeError:
                    # Se _load_post_and_files não existir (versões mais antigas)
                    # ou se o request.body já foi consumido, podemos tentar uma abordagem alternativa.
                    # Mas o erro 'request' indica que o problema é na integração.
                    pass # O ideal é que isso funcione. Se falhar, é um problema mais fundamental.

                request.method = original_method # Restaura o método original

                # Agora, request.POST e request.FILES devem estar populados
                bio = request.POST.get('bio', user.bio or '')
                username = request.POST.get('username')
                profile_picture = request.FILES.get('profile_picture')
                old_password = request.POST.get('old_password')
                new_password = request.POST.get('new_password')
                remove_profile_picture = request.POST.get('remove_profile_picture', 'false').lower() == 'true'

                logger.debug(f"Dados parseados (Forced POST/FILES) POST: {dict(request.POST)}")
                logger.debug(f"Dados parseados (Forced POST/FILES) FILES: {dict(request.FILES)}")

            elif request.content_type.startswith('application/json'):
                data = json.loads(request.body)
                bio = data.get('bio', user.bio or '')
                username = data.get('username')
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                profile_picture = None # Não há upload de arquivo direto via JSON
                remove_profile_picture = data.get('remove_profile_picture', False)
            else:
                logger.warning(f"Tipo de conteúdo inesperado: {request.content_type}. Acessando request.POST/FILES diretamente.")
                # Este else é um fallback, mas se for multipart/form-data,
                # o bloco acima DEVE ter populado request.POST/FILES.
                bio = request.POST.get('bio', user.bio or '')
                username = request.POST.get('username')
                profile_picture = request.FILES.get('profile_picture')
                old_password = request.POST.get('old_password')
                new_password = request.POST.get('new_password')
                remove_profile_picture = request.POST.get('remove_profile_picture', 'false').lower() == 'true'


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
            logger.error(f"Erro ao atualizar perfil: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método inválido'}, status=400)