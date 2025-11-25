from pathlib import Path
import os
import environ
import boto3
from botocore.exceptions import ClientError


def get_ssm_param(name, default=None):
    """
    Retrieve parameter from AWS SSM Parameter Store (SecureString).
    Falls back to default if any error occurs.
    """
    try:
        ssm = boto3.client("ssm", region_name="us-east-1")
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception:
        return default


# Environment setup
env = environ.Env(DEBUG=(bool, False))
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env in local development only
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Default to production in Elastic Beanstalk
ENVIRONMENT = env('ENVIRONMENT', default='production')


# Security
SECRET_KEY = get_ssm_param("/italians/SECRET_KEY", env("SECRET_KEY", default="dummy"))
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = ["*"]


# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'menu',
    'orders',
    'users',
    'storages',
    'cloud_notify',
]


# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'italians_by_the_bay.urls'


# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'italians_by_the_bay.wsgi.application'


# Database
if ENVIRONMENT == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/var/app/data/db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Authentication redirects
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/users/login/'


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Email configuration (SSM + fallback)
EMAIL_BACKEND = env('EMAIL_BACKEND', default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env('EMAIL_HOST', default="smtp.gmail.com")
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)

EMAIL_HOST_USER = get_ssm_param("/italians/EMAIL_HOST_USER", env("EMAIL_HOST_USER", default=""))
EMAIL_HOST_PASSWORD = get_ssm_param("/italians/EMAIL_HOST_PASSWORD", env("EMAIL_HOST_PASSWORD", default=""))
DEFAULT_FROM_EMAIL = get_ssm_param("/italians/DEFAULT_FROM_EMAIL", env("DEFAULT_FROM_EMAIL", default="no-reply@example.com"))


# Media storage (S3)
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "italians-by-the-bay-media")
AWS_S3_REGION_NAME = os.getenv("AWS_REGION", "us-east-1")
AWS_QUERYSTRING_AUTH = False

MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
MEDIA_ROOT = ""
