from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from .models import Post, PostAction
import json
import logging
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request as DRFRequest
from rest_framework.exceptions import ParseError
from django.utils.text import slugify
import os
import cloudinary.uploader
import cloudinary
import time

logger = logging.getLogger(__name__)

User = get_user_model()

# Post views (não alterados, pois não usam as funções de auth do Django)
# ----------------------------------------------------------------------
class PostList(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        posts = Post.objects.all().order_by('-created_at')
        data = [
            {
                'id': post.id,
                'text': post.text,
                'author': post.author.username,
                'likes_count': post.likes_count,
                'reposts_count': post.reposts_count,
                'comments_count': post.comments_count,
                'shares_count': post.shares_count,
                'created_at': post.created_at.isoformat(),
                'image': post.image if post.image else ''
            }
            for post in posts
        ]
        return Response({'posts': data})

class PostCreate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if request.content_type.startswith('multipart/form-data'):
                # Usando o nome 'drf_request' para evitar confusão
                drf_request = DRFRequest(request, parsers=[MultiPartParser()])
                data = drf_request.data
                files = drf_request.FILES
                text = data.get('text')
                image = files.get('image')
                if not text and not image:
                    return Response({'detail': 'Post must have text or an image'}, status=status.HTTP_400_BAD_REQUEST)

                post = Post(author=request.user, text=text if text else '')
                if image:
                    name, ext = os.path.splitext(image.name)
                    sanitized_name = f"{slugify(name)}_{os.urandom(8).hex()}{ext.lower()}"
                    current_timestamp = int(time.time())
                    logger.debug(f"Generated timestamp: {current_timestamp} for upload")
                    if current_timestamp < 1700000000:
                        return Response({'detail': 'Timestamp inválido'}, status=status.HTTP_400_BAD_REQUEST)
                    cloudinary.config(
                        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                        api_key=os.getenv('CLOUDINARY_API_KEY'),
                        api_secret=os.getenv('CLOUDINARY_API_SECRET')
                    )
                    upload_result = cloudinary.uploader.upload(
                        image,
                        folder="post_pics",
                        public_id=sanitized_name,
                        overwrite=True,
                        timestamp=current_timestamp
                    )
                    post.image = upload_result['secure_url']
                    logger.debug(f"Post created with image: id={post.id}, url={post.image}")
                post.save()
                return Response({
                    'id': post.id,
                    'text': post.text,
                    'author': request.user.username,
                    'image': post.image if post.image else '',
                    'created_at': post.created_at.isoformat()
                })
            else:
                data = json.loads(request.body)
                text = data.get('text')
                if text:
                    post = Post.objects.create(author=request.user, text=text)
                    logger.debug(f"Post created: id={post.id}, author={request.user.username}")
                    return Response({
                        'id': post.id,
                        'text': post.text,
                        'author': request.user.username,
                        'image': '',
                        'created_at': post.created_at.isoformat()
                    })
                return Response({'detail': 'Texto ausente'}, status=status.HTTP_400_BAD_REQUEST)
        except json.JSONDecodeError:
            return Response({'detail': 'JSON inválido'}, status=status.HTTP_400_BAD_REQUEST)
        except ParseError as e:
            logger.error(f"Erro de parsing: {e}")
            return Response({'detail': f'Falha ao processar dados: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro ao criar post: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PostActions(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        actions = PostAction.objects.filter(user=request.user, post=post).values('action_type')
        action_list = list(actions)
        logger.debug(f"Ações do post {post_id}: {action_list}")
        return Response({'actions': action_list})

class PostLike(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        action = PostAction.objects.filter(user=request.user, post=post, action_type='like').first()
        if action:
            action.delete()
            post.likes_count = max(0, post.likes_count - 1)
            logger.debug(f"Like removido do post {post_id}: likes_count={post.likes_count}")
        else:
            PostAction.objects.create(user=request.user, post=post, action_type='like')
            post.likes_count += 1
            logger.debug(f"Like adicionado ao post {post_id}: likes_count={post.likes_count}")
        post.save()
        return Response({'likes_count': post.likes_count, 'id': post.id})

    def delete(self, request, post_id):
        return self.post(request, post_id)

class PostRepost(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        action = PostAction.objects.filter(user=request.user, post=post, action_type='repost').first()
        if action:
            action.delete()
            post.reposts_count = max(0, post.reposts_count - 1)
            logger.debug(f"Repost removido do post {post_id}: reposts_count={post.reposts_count}")
        else:
            PostAction.objects.create(user=request.user, post=post, action_type='repost')
            post.reposts_count += 1
            logger.debug(f"Repost adicionado ao post {post_id}: reposts_count={post.reposts_count}")
        post.save()
        return Response({'reposts_count': post.reposts_count, 'id': post.id})

    def delete(self, request, post_id):
        return self.post(request, post_id)

class PostComment(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        action = PostAction.objects.filter(user=request.user, post=post, action_type='comment').first()
        if action:
            action.delete()
            post.comments_count = max(0, post.comments_count - 1)
            logger.debug(f"Comentário removido do post {post_id}: comments_count={post.comments_count}")
        else:
            PostAction.objects.create(user=request.user, post=post, action_type='comment')
            post.comments_count += 1
            logger.debug(f"Comentário adicionado ao post {post_id}: comments_count={post.comments_count}")
        post.save()
        return Response({'comments_count': post.comments_count, 'id': post.id})

    def delete(self, request, post_id):
        return self.post(request, post_id)

class PostShare(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        action = PostAction.objects.filter(user=request.user, post=post, action_type='share').first()
        if action:
            action.delete()
            post.shares_count = max(0, post.shares_count - 1)
            logger.debug(f"Compartilhamento removido do post {post_id}: shares_count={post.shares_count}")
        else:
            PostAction.objects.create(user=request.user, post=post, action_type='share')
            post.shares_count += 1
            logger.debug(f"Compartilhamento adicionado ao post {post_id}: shares_count={post.shares_count}")
        post.save()
        return Response({'shares_count': post.shares_count, 'id': post.id})

    def delete(self, request, post_id):
        return self.post(request, post_id)

class FeedList(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        following_users = request.user.following.all()
        posts = Post.objects.filter(author__in=following_users).order_by('-created_at')
        data = [
            {
                'id': post.id,
                'text': post.text,
                'author': post.author.username,
                'likes_count': post.likes_count,
                'reposts_count': post.reposts_count,
                'comments_count': post.comments_count,
                'shares_count': post.shares_count,
                'image': post.image if post.image else '',
                'created_at': post.created_at.isoformat()
            }
            for post in posts
        ]
        logger.debug(f"Feed response: {{'posts': {data}}}")
        return Response({'posts': data})

class FollowUser(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        user_to_follow = get_object_or_404(User, id=user_id)
        if user_to_follow != request.user:
            if request.user.following.filter(id=user_id).exists():
                request.user.following.remove(user_to_follow)
            else:
                request.user.following.add(user_to_follow)
        logger.debug(f"Follow atualizado: user={request.user.username}, target={user_to_follow.username}")
        return Response({'status': 'updated', 'following_count': request.user.following.count()})

    def delete(self, request, user_id):
        return self.post(request, user_id)

class UserSuggestions(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.exclude(id=request.user.id).values('id', 'username') if request.user.is_authenticated else User.objects.all().values('id', 'username')[:5]
        return Response({'suggestions': list(users)})

class Profile(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile_data = {
            'username': user.username,
            'handle': user.username.lower(),
            'bio': user.bio or '',
            'location': user.location or '',
            'profile_picture': user.profile_picture if user.profile_picture else '',
            'cover_image': user.cover_image if user.cover_image else '',
            'followers': user.followers_set.count(),
            'following': user.following.count(),
            'posts_count': user.posts.count(),
        }
        logger.debug(f"Profile response: {profile_data}")
        return Response(profile_data)

class ProfilePosts(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = Post.objects.filter(author=request.user).order_by('-created_at')
        data = [
            {
                'id': post.id,
                'text': post.text,
                'author': post.author.username,
                'likes_count': post.likes_count,
                'reposts_count': post.reposts_count,
                'comments_count': post.comments_count,
                'shares_count': post.shares_count,
                'image': post.image if post.image else '',
                'created_at': post.created_at.isoformat()
            }
            for post in posts
        ]
        logger.debug(f"Profile posts response: {{'posts': {data}}}")
        return Response({'posts': data})

# ----------------------------------------
# Vistas de Autenticação Corrigidas
# ----------------------------------------
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug("Login view acessada, CSRF desativado")
        try:
            data = request.data
            username = data.get('username')
            password = data.get('password')
            if not username or not password:
                logger.warning("Campos de login ausentes")
                return Response({'detail': 'Username e senha são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro ao decodificar dados: {e}")
            return Response({'detail': 'JSON inválido'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request=request._request, username=username, password=password)
        if user is not None:
            login(request._request, user)
            token, created = Token.objects.get_or_create(user=user)
            logger.debug(f"Login bem-sucedido: {username}, Token: {token.key}")
            return Response({'status': 'success', 'username': user.username, 'token': token.key})
        logger.warning(f"Login falhou: {username}")
        return Response({'detail': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug("Register view acessada, CSRF desativado")
        try:
            data = request.data
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            logger.debug(f"JSON parseado: username={username}, email={email}")
        except Exception as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return Response({'detail': 'JSON inválido'}, status=status.HTTP_400_BAD_REQUEST)

        if not username or not password or not email:
            logger.warning("Campos obrigatórios ausentes no registro")
            return Response({'detail': 'Todos os campos são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            logger.warning(f"Registro falhou: usuário {username} já existe")
            return Response({'detail': 'Usuário já existe'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            login(request._request, user)
            token, created = Token.objects.get_or_create(user=user)
            logger.debug(f"Registro bem-sucedido: {username}, Token: {token.key}")
            return Response({'status': 'success', 'username': user.username, 'token': token.key})
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            return Response({'detail': 'Falha ao criar usuário'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        logout(request._request)
        logger.debug("Logout bem-sucedido")
        return Response({'status': 'success'})

# ----------------------------------------
# Vista de Atualização de Perfil Corrigida
# ----------------------------------------
class ProfileUpdate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        try:
            # Não é necessário o drf_request = Request(request, ...) pois request já é um DRF Request
            # e a classe APIView já faz a gestão do body. O seu código já tem a lógica para 
            # MultiPartParser e application/json, que funciona com request.data e request.FILES
            # quando a APIView usa esses parsers.
            
            data = request.data

            bio = data.get('bio', user.bio or '')
            username = data.get('username')
            profile_picture = data.get('profile_picture')
            old_password = data.get('old_password')
            new_password = data.get('new_password')
            remove_profile_picture = str(data.get('remove_profile_picture', 'false')).lower() == 'true'

            logger.debug(f"Dados parseados: POST={dict(data)}")
            
            if 'profile_picture' in request.FILES:
                profile_picture = request.FILES['profile_picture']

            if profile_picture and isinstance(profile_picture, DRFRequest):
                # Este bloco trata o caso onde profile_picture é um objeto de request, 
                # o que pode ser uma fonte de erro.
                return Response({'detail': 'Objeto de arquivo inválido'}, status=status.HTTP_400_BAD_REQUEST)

            if profile_picture and not isinstance(profile_picture, str):
                name, ext = os.path.splitext(profile_picture.name)
                sanitized_name = f"{slugify(name)}_{os.urandom(8).hex()}{ext.lower()}"
                current_timestamp = int(time.time())
                logger.debug(f"Generated timestamp: {current_timestamp}")
                if current_timestamp < 1700000000:
                    return Response({'detail': 'Timestamp inválido'}, status=status.HTTP_400_BAD_REQUEST)
                cloudinary.config(
                    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                    api_key=os.getenv('CLOUDINARY_API_KEY'),
                    api_secret=os.getenv('CLOUDINARY_API_SECRET')
                )
                upload_result = cloudinary.uploader.upload(
                    profile_picture,
                    folder="profile_pics",
                    public_id=sanitized_name,
                    overwrite=True,
                    timestamp=current_timestamp
                )
                user.profile_picture = upload_result['secure_url']
                logger.debug(f"Profile picture uploaded: url={user.profile_picture}")

            logger.debug(f"Dados processados: username={username!r}, bio={bio!r}, old_password={old_password!r}, new_password={new_password!r}")

            if not username:
                logger.warning("Username vazio")
                return Response({'detail': 'Nome de usuário é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
            if len(username) < 3:
                logger.warning(f"Username muito curto: {username}")
                return Response({'detail': 'O nome de usuário deve ter pelo menos 3 caracteres'}, status=status.HTTP_400_BAD_REQUEST)
            if username != user.username and User.objects.filter(username=username).exists():
                logger.warning(f"Username já existe: {username}")
                return Response({'detail': 'Nome de usuário já existe'}, status=status.HTTP_400_BAD_REQUEST)

            if new_password and old_password and new_password.strip() and old_password.strip():
                if not authenticate(request._request, username=user.username, password=old_password):
                    logger.warning("Senha antiga inválida")
                    return Response({'detail': 'Senha antiga inválida'}, status=status.HTTP_400_BAD_REQUEST)
                user.set_password(new_password)

            user.username = username
            user.bio = bio
            if remove_profile_picture and user.profile_picture:
                user.profile_picture = None
                logger.info("Profile picture removed")

            user.save()
            logger.debug(f"Saved: username={user.username}, profile_picture={user.profile_picture if user.profile_picture else ''}")

            return Response({
                'status': 'success',
                'username': user.username,
                'bio': user.bio or '',
                'location': user.location or '',
                'profile_picture': user.profile_picture if user.profile_picture else '',
                'cover_image': user.cover_image if user.cover_image else ''
            })
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)