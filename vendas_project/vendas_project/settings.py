import os
from pathlib import Path
import dj_database_url
import cloudinary



BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 Segurança
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev')

#DEBUG = os.getenv('DEBUG', 'False') == 'True' usar no suPer user
DEBUG = True

ALLOWED_HOSTS = ['.onrender.com',
                'mirnaboutique.com',
                '.mirnaboutique.com',
                ]

CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com',
                       'https://*.mirnaboutique.com',
                       ]


# ========================================== #
# CACHE CONFIGURATION                        #
# ========================================== #

# 🔥 Configuração de cache (armazenamento em memória)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'mirna-boutique-cache',
        'TIMEOUT': 300,  # 5 minutos
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# 🔥 Tempo de cache por tipo de página (em segundos)
CACHE_TIMEOUTS = {
    'pagina_inicial': 600,      # 10 minutos
    'detalhes_produto': 3600,   # 1 hora
    'lista_produtos': 600,      # 10 minutos
    'categorias': 3600,         # 1 hora
}

# 🔥 URLs que NÃO devem ter cache
CACHE_EXCLUDED_URLS = [
    '/carrinho/',
    '/checkout/',
    '/login/',
    '/registrar/',
    '/meus-pedidos/',
    '/admin/',
]
#--------------------------------------------------------------
# 🔐 Segurança HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Configurações da Sessão
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 semanas
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # 🔥 ADICIONE ESTA LINHA

# Aplicações
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'widget_tweaks',
    'mathfilters',
    'vendas',

    # ☁️ Cloudinary (gravar img no na nuvem)
    'cloudinary',
    'cloudinary_storage',
]
# ☁️ Configuração Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
)
CLOUDINARY_STORAGE = {
    'UPLOAD_OPTIONS': {
        'folder': 'vendas_project/produtos'
    }
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ⚙️ Middleware correto
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # importante no Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vendas_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Já existe
            BASE_DIR / 'vendas' / 'templates',  # ← ADICIONE ESTA LINHA
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'vendas.context_processors.mercadopago_settings',
                'vendas.context_processors.carrinho_count',  # ← Contador carrinho
            ],
        },
    },
]


WSGI_APPLICATION = 'vendas_project.wsgi.application'

# 🗄️ Banco (NEON)
DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=60,
        ssl_require=True
    )
}

# Senhas
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 🌎 Localização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# 📦 Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# 📁 Media
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# 🔑 Login
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ⏱️ Tempo de expiração do link de reset de senha (em segundos)
PASSWORD_RESET_TIMEOUT = 3600  # 1 hora

# Recuperação de senha

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 2525
EMAIL_USE_SSL = False
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'b64349001@smtp-brevo.com'
EMAIL_HOST_PASSWORD = 'bskTOoBSUdEHrFQ'  # ← SENHA DE APP (brevo) lembrar de criar Variavel ENV para mascarar!
DEFAULT_FROM_EMAIL = 'Mirna Boutique <mirnaboutique@mirnaboutique.com>'
PASSWORD_RESET_TIMEOUT = 3600


# 💳 Mercado Pago (NUNCA hardcoded)
MERCADOPAGO_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN')
MERCADOPAGO_PUBLIC_KEY = os.getenv('MP_PUBLIC_KEY')
MERCADOPAGO_SANDBOX = os.getenv('MP_SANDBOX', 'False') == 'True'
