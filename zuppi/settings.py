from dotenv import load_dotenv
load_dotenv()
import os
from pathlib import Path
try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Determine the environment (production or development)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-_um@@ac&hg&^o^c8p37j7nbiu8#_6vin-ft7_fpm@(4)4cnjfj')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ENVIRONMENT != 'production'

# Allow Render's domain in production and localhost for development
# CORREÇÃO: Removido 'https://' do ALLOWED_HOSTS para o Vercel URL.
if ENVIRONMENT == 'production':
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'zuppi-backend.onrender.com', 'zuppi.vercel.app']
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'social',  # Your custom app
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first for CORS
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', # Mantenha esta linha aqui, ela é que exige o token CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings for React frontend
# USANDO CORS_ALLOWED_ORIGIN_REGEXES para flexibilidade com a barra final
if ENVIRONMENT == 'production':
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https:\/\/zuppi\.vercel\.app\/?$", # Permite com ou sem barra final (usando /?)
    ]
else:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^http:\/\/localhost:3000\/?$",
        r"^http:\/\/localhost:5173\/?$",
    ]

CORS_ALLOW_CREDENTIALS = True

# >>> Adicione esta linha crucial para permitir os cabeçalhos do frontend! <<<
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
    'pragma',
]

# CSRF settings
# Incluindo explicitamente ambas as variações (com e sem barra final) e o backend do Render
if ENVIRONMENT == 'production':
    CSRF_TRUSTED_ORIGINS = [
        'https://zuppi.vercel.app',
        'https://zuppi.vercel.app/',
        'https://zuppi-backend.onrender.com', # Adicionada para compatibilidade extra
    ]
    # >>> ADIÇÕES CRUCIAIS PARA O COOKIE CSRF <<<
    CSRF_COOKIE_DOMAIN = 'zuppi.vercel.app' # Define o domínio para o cookie CSRF
    CSRF_COOKIE_SECURE = True # Garante que o cookie só é enviado via HTTPS
    CSRF_COOKIE_SAMESITE = 'None' # Permite envio cross-site (requer Secure=True)
else:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
    ]
    # >>> ADIÇÕES PARA AMBIENTE DE DESENVOLVIMENTO <<<
    CSRF_COOKIE_DOMAIN = None # Permite que o Django defina o domínio automaticamente para localhost
    CSRF_COOKIE_SECURE = False # Não precisa de HTTPS em desenvolvimento
    CSRF_COOKIE_SAMESITE = 'Lax' # Ou 'None' com secure=True, mas Lax é mais seguro para localhost

ROOT_URLCONF = 'zuppi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'zuppi.wsgi.application'

# Database
if ENVIRONMENT == 'production' and os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(
            os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cache configuration
if ENVIRONMENT == 'development':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (e.g., profile pictures)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'social.CustomUser'

# Login URL
LOGIN_URL = '/accounts/login/'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if ENVIRONMENT == 'production' else 'DEBUG',
    },
}