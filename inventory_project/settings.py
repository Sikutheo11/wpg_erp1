import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/


def _environment_boolean(name, default=False):
    value = os.environ.get(
        name,
        "True" if default else "False",
    )
    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _environment_list(name, default=""):
    return [
        value.strip()
        for value in os.environ.get(
            name,
            default,
        ).split(",")
        if value.strip()
    ]

def _required_environment(name):
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"{name} environment variable is required."
        )

    return value


DEBUG = _environment_boolean(
    "DJANGO_DEBUG",
    default=True,
)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    (
        "dev-only-secret-key-change-this-before-production-"
        "wpg-bos-local-development"
    ),
)

if not DEBUG and not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError(
        "DJANGO_SECRET_KEY is required when DEBUG is False."
    )


ALLOWED_HOSTS = _environment_list(
    "DJANGO_ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
)

CSRF_TRUSTED_ORIGINS = _environment_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.humanize",
    'crispy_forms',
    'accounts',
    "inventory.apps.InventoryConfig",
    "finance.apps.FinanceConfig",
    'furniture.apps.FurnitureConfig',
    "sales.apps.SalesConfig",
    "Employee.apps.EmployeeConfig",
    'core',
    'rest_framework',
    'corsheaders',
    "ecommerce.apps.EcommerceConfig",
    'Construction.apps.ConstructionConfig',
    'orders.apps.OrdersConfig',
    'agriculture'
    
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'inventory_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Add custom templates directory if you have one
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.dashboard_context',
                "ecommerce.context_processors.ecommerce_cart",
            ],
        },
    },
]

WSGI_APPLICATION = 'inventory_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _required_environment(
            "POSTGRES_DB"
        ),
        "USER": _required_environment(
            "POSTGRES_USER"
        ),
        "PASSWORD": _required_environment(
            "POSTGRES_PASSWORD"
        ),
        "HOST": _required_environment(
            "POSTGRES_HOST"
        ),
        "PORT": os.environ.get(
            "POSTGRES_PORT",
            "5432",
        ),
        "CONN_MAX_AGE": int(
            os.environ.get(
                "POSTGRES_CONN_MAX_AGE",
                "0" if DEBUG else "60",
            )
        ),
        "OPTIONS": {
            "sslmode": os.environ.get(
                "POSTGRES_SSLMODE",
                "prefer",
            ),
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}
# Media files (Uploads)
# https://docs.djangoproject.com/en/5.0/howto/static-files/#serving-files-uploaded-by-a-user-during-development
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = 'index'  # Change 'index' to your desired redirect URL after login
LOGOUT_REDIRECT_URL = 'login'  # Change 'login' to your desired redirect URL after logout
# settings.py
AUTH_USER_MODEL = 'accounts.User'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ]
}

# ALLOWED_HOSTS = ["wpg_erp.onrender.com"]  # later replace with your domain

ECOMMERCE_PAYMENT_CALLBACK_BASE_URL = (
    os.environ.get(
        "ECOMMERCE_PAYMENT_CALLBACK_BASE_URL",
        "",
    )
    .strip()
    .rstrip("/")
)

# Production HTTPS and cookie security.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_HSTS_SECONDS = (
    3600
    if not DEBUG
    else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"