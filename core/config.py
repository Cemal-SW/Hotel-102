from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / 'data'
INSTANCE_DIR = DATA_DIR / 'instance'
UPLOADS_DIR = DATA_DIR / 'uploads'


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def env_list(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, '')
    return tuple(item.strip() for item in raw.split(',') if item.strip())


def get_runtime_environment() -> str:
    return os.environ.get('HOTEL102_ENV', 'development').strip().lower() or 'development'


def is_production() -> bool:
    return get_runtime_environment() == 'production'


def is_debug_enabled() -> bool:
    return env_bool('FLASK_DEBUG', not is_production())


def get_secret_key() -> str:
    secret_key = os.environ.get('FLASK_SECRET_KEY', '').strip()
    if secret_key:
        return secret_key
    if is_production():
        raise RuntimeError('FLASK_SECRET_KEY must be set when HOTEL102_ENV=production.')
    return 'hotel102-dev-only-secret-key'


def get_database_uri() -> str:
    database_url = os.environ.get('DATABASE_URL', '').strip()
    if database_url:
        return database_url
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    return 'sqlite:///' + str((INSTANCE_DIR / 'hotel.db').resolve())


class BaseConfig:
    SECRET_KEY = get_secret_key()
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD = is_debug_enabled()
    SEND_FILE_MAX_AGE_DEFAULT = 0 if is_debug_enabled() else 3600
    MAX_CONTENT_LENGTH = env_int('MAX_UPLOAD_BYTES', 50 * 1024 * 1024)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', is_production())
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.environ.get('REMEMBER_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_SECURE = env_bool('REMEMBER_COOKIE_SECURE', is_production())
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=env_int('SESSION_LIFETIME_SECONDS', 60 * 60 * 8))
    BOOKING_URL = os.environ.get('BOOKING_URL', 'http://127.0.0.1:5001/').strip() or 'http://127.0.0.1:5001/'
    MAIN_URL = os.environ.get('MAIN_URL', 'http://127.0.0.1:5000/').strip() or 'http://127.0.0.1:5000/'
    BOOKING_PUBLIC_URL = os.environ.get('BOOKING_PUBLIC_URL', '').strip()
    TRUST_PROXY_HEADERS = env_bool('TRUST_PROXY_HEADERS', False)
    BUILD_BOOKING_CSS_ON_REQUEST = env_bool('BUILD_BOOKING_CSS_ON_REQUEST', False)
    ADMIN_RATE_LIMIT_ATTEMPTS = env_int('ADMIN_RATE_LIMIT_ATTEMPTS', 5)
    ADMIN_RATE_LIMIT_WINDOW_SECONDS = env_int('ADMIN_RATE_LIMIT_WINDOW_SECONDS', 15 * 60)
    ADMIN_ALLOWED_IPS = env_list('ADMIN_ALLOWED_IPS')
    ADMIN_BASIC_AUTH_USERNAME = os.environ.get('ADMIN_BASIC_AUTH_USERNAME', '').strip()
    ADMIN_BASIC_AUTH_PASSWORD = os.environ.get('ADMIN_BASIC_AUTH_PASSWORD', '').strip()
    SECURITY_HEADERS_ENABLED = env_bool('SECURITY_HEADERS_ENABLED', True)
    FORCE_HTTPS_REDIRECT = env_bool('FORCE_HTTPS_REDIRECT', False)
    LOG_ADMIN_EVENTS = env_bool('LOG_ADMIN_EVENTS', True)
    UPLOAD_FOLDER = str(UPLOADS_DIR.resolve())
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    ALLOWED_IMAGE_MIME_PREFIXES = ('image/',)
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4'}
    ALLOWED_VIDEO_MIME_TYPES = {'video/mp4'}
    PUBLIC_UPLOAD_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
    IYZICO_MODE = os.environ.get('IYZICO_MODE', 'sandbox').strip().lower() or 'sandbox'
    IYZICO_BASE_URL = os.environ.get('IYZICO_BASE_URL', '').strip()
