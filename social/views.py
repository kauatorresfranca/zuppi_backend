from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token # Removido csrf_exempt daqui
from .models import Post, PostAction
import json
import logging
from django.views.decorators.cache import never_cache

# --- IMPORTAÇÕES NECESSÁRIAS PARA O PARSING COM DRF MultiPartParser ---
# Garanta que 'rest_framework' esteja no seu INSTALLED_APPS em settings.py
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request # Essencial para criar a request do DRF
from rest_framework.exceptions import ParseError # Para capturar erros de parsing
from io import BytesIO # Necessário para recriar o stream da requisição

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

# Removido @csrf_exempt
def login_view(request):
    if request.method == 'POST':
        # O Django e o DRF sabem como lidar com request.POST e request.body
        # sem quebrar a validação do CSRF.
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

# Removido @csrf_exempt
def register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
        except json.JSONDecodeError:
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
    token = get_token(request)
    logger.debug(f"CSRF token gerado: {token}")
    return JsonResponse({'csrfToken': token})

# Removido @csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        logger.debug("Logout bem-sucedido")
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Método inválido'}, status=400)

@login_required
def profile_update(request):
    if request.method == 'PATCH':
        user = request.user
        try:
            # Captura o corpo da requisição bruta ANTES de qualquer leitura
            raw_body = request.body

            logger.debug(f"Request headers: {dict(request.headers)}")
            logger.debug(f"Content-Type: {request.content_type}")
            logger.debug(f"Raw request body length: {len(raw_body)}")
            logger.debug(f"Raw request body: {raw_body.decode('utf-8', errors='ignore')}")

            data = None # Para armazenar os dados de texto do formulário
            files = None # Para armazenar os dados de arquivo

            if request.content_type.startswith('multipart/form-data'):
                # --- Lógica de parsing usando DRF MultiPartParser para PATCH ---
                try:
                    # O MultiPartParser espera um objeto de request que tenha .stream e .META
                    # A classe Request do DRF é perfeita para isso, pois ela envolve a HttpRequest original.
                    # É CRÍTICO que o request.body não seja lido ANTES disso, exceto para o log.
                    # Como já lemos para o log (raw_body), precisamos recriar o stream.

                    # Crie um HttpRequest "mock" que MultiPartParser possa entender.
                    # Definimos ._body e ._stream para que o parser possa lê-lo.
                    # O Request do DRF internamente vai usar request.body para preencher ._stream
                    # se ele ainda não foi lido. Como já lemos, precisamos garantir que o stream
                    # seja passado corretamente ou resetado.

                    # A maneira mais segura é passar o HttpRequest original para o Request do DRF.
                    # Ele vai gerenciar o acesso ao stream.

                    # Resetar o stream do HttpRequest original se ele já foi consumido
                    # A propriedade `request.body` já consome o stream.
                    # Para que o DRF Request possa ler, precisamos "rebobinar" ou recriar o stream.
                    # Uma forma mais direta para garantir que o DRF Request receba um stream limpo:

                    # Cria um Request do DRF. Ele irá encapsular o HttpRequest original.
                    # O DRF Request sabe como lidar com o corpo da HttpRequest.
                    # E o DRF Request é o objeto que o MultiPartParser espera.

                    # Vamos criar um request temporário que o DRF Request possa envolver.
                    # Isso é feito pelo construtor de Request do DRF.
                    # Apenas precisamos garantir que o HttpRequest original não tenha seu stream consumido
                    # antes de ser passado para o Request do DRF.
                    # A leitura de `request.body` para logging já consumiu, então essa é a complicação.

                    # O jeito mais limpo é o DRF Request fazer a leitura do corpo.
                    # Mas se já lemos para log, precisamos fazer o Django Request acessível novamente.
                    # Para isso, redefinimos `_read_started` e `_stream` do HttpRequest original.

                    if hasattr(request, '_read_started'): # Para Django > 2.0
                        request._read_started = False
                    if hasattr(request, '_stream'):
                        request._stream.seek(0) # Rebobina o stream se ele já foi lido e é um BytesIO
                    else: # Caso o stream ainda não tenha sido criado ou seja de outro tipo
                        request._stream = BytesIO(raw_body)
                        request.read = request._stream.read # Garante que request.read() funcione


                    # Agora, crie a request do DRF que envolve a request do Django
                    drf_request = Request(request, parsers=[MultiPartParser()])

                    # O DRF Request tem seus próprios .data e .FILES que já foram populados
                    # pelos parsers configurados durante a inicialização.
                    data = drf_request.data
                    files = drf_request.FILES

                except ParseError as e:
                    logger.error(f"Erro de parsing de multipart/form-data com DRF MultiPartParser: {e}")
                    return JsonResponse({'error': f'Falha ao processar dados de formulário: {e}'}, status=400)
                except Exception as e:
                    logger.error(f"Erro inesperado ao usar DRF MultiPartParser: {e.__class__.__name__}: {e}")
                    return JsonResponse({'error': f'Erro inesperado no parsing: {e}'}, status=400)

                # Extrai os dados dos objetos QueryDict/Dict retornado pelo parser
                # drf_request.data e drf_request.FILES já são QueryDicts ou semelhantes a dicionários
                bio = data.get('bio', user.bio or '')
                username = data.get('username')
                profile_picture = files.get('profile_picture')
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                # Note que 'remove_profile_picture' vem como string 'true'/'false' de form-data
                remove_profile_picture = data.get('remove_profile_picture', 'false').lower() == 'true'

                logger.debug(f"Dados parseados (multipart): POST={dict(data)}, FILES={dict(files)}")

            elif request.content_type.startswith('application/json'):
                # Mantém a lógica existente para JSON, caso você a use
                data_json = json.loads(raw_body) # Usa raw_body aqui também
                bio = data_json.get('bio', user.bio or '')
                username = data_json.get('username')
                old_password = data_json.get('old_password')
                new_password = data_json.get('new_password')
                profile_picture = None # Não há upload de arquivo direto via JSON
                remove_profile_picture = data_json.get('remove_profile_picture', False)
                logger.debug(f"Dados parseados (JSON): {data_json}")
            else:
                # Retorna erro se o Content-Type não for nem multipart/form-data nem application/json
                logger.warning(f"Tipo de conteúdo inesperado para PATCH: {request.content_type}")
                return JsonResponse({'error': 'Tipo de conteúdo não suportado para esta operação.'}, status=415) # 415 Unsupported Media Type

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