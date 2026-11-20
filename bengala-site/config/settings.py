import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

# Driver do banco em Python puro: instala na Vercel sem compilar nada.
# Funciona igual com o MariaDB do PC e com o TiDB Cloud.
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

# Senhas e chaves ficam no arquivo .env (fora do Git). Variáveis já
# definidas no terminal têm prioridade sobre o .env.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "core",
    "painel",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Banco: MariaDB no PC ou TiDB Cloud em produção (Vercel). A estrutura das
# tabelas vem do schema.sql; o Django só cria as tabelas dele mesmo
# (auth_user, django_session...).
#   PC:     DB_ENGINE vazio (usa o MySQL/MariaDB padrão do Django), DB_SSL=False
#   Vercel: DB_ENGINE=django_tidb, DB_SSL=True
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE") or "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "bengala"),
        "USER": os.getenv("DB_USER", "api_bengala"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            # O banco guarda horário de Manaus (-04:00, sem horário de verão).
            # Fixar o fuso da conexão faz o CURRENT_TIMESTAMP das tabelas
            # gravar o mesmo horário que o Django, no PC e na nuvem (UTC).
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone='-04:00'",
        },
    }
}

# O TiDB Cloud só aceita conexão criptografada (TLS).
if os.getenv("DB_SSL", "False") == "True":
    import certifi

    DATABASES["default"]["OPTIONS"]["ssl"] = {"ca": certifi.where()}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Login do site pelo e-mail, e só para administradores (is_staff).
AUTHENTICATION_BACKENDS = ["painel.autenticacao.EmailBackend"]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "painel"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"

# O banco guarda DATETIME sem fuso, no horário local. Com USE_TZ = False o
# Django lê e grava exatamente o que está no banco, sem converter para UTC.
TIME_ZONE = "America/Manaus"
USE_I18N = True
USE_TZ = False

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# API do app: só por token (cabeçalho "Authorization: Token <chave>").
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "COERCE_DECIMAL_TO_STRING": False,
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    # Na Vercel o HTTPS termina no proxy dela, que avisa por este cabeçalho.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SEGURO", "False") == "True"
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
