from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, null=True)
    following = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='followers_set')

    # Adicionar related_name aos campos herdados para evitar conflitos
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',  # Nome único para o acessor reverso
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',  # Nome único para o acessor reverso
        blank=True,
    )

    def __str__(self):
        return self.username

# Modelo para Post
class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    likes_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.author.username}: {self.text[:20]}'

# Relações ManyToMany para ações (curtidas, reposts, comentários, compartilhamentos)
class PostAction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    action_type = models.CharField(
        max_length=20,
        choices=[
            ('like', 'Like'),
            ('repost', 'Repost'),
            ('comment', 'Comment'),
            ('share', 'Share'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post', 'action_type')  # Evita duplicatas

    def __str__(self):
        return f'{self.user.username} {self.action_type} on {self.post.id}'