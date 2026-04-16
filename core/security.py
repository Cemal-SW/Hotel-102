from __future__ import annotations

import base64
import hmac
import ipaddress
import secrets
import time
from collections import defaultdict, deque
from typing import Iterable

from flask import abort, current_app, request, session
from werkzeug.exceptions import BadRequest


_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def get_request_ip() -> str:
    if current_app.config.get('TRUST_PROXY_HEADERS'):
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def request_is_secure() -> bool:
    return request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https'


def enforce_https_redirect():
    if not current_app.config.get('FORCE_HTTPS_REDIRECT'):
        return None
    if request_is_secure():
        return None
    if current_app.debug:
        return None
    secure_url = request.url.replace('http://', 'https://', 1)
    from flask import redirect
    return redirect(secure_url, code=301)


def generate_csrf_token() -> str:
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def csrf_input_html() -> str:
    token = generate_csrf_token()
    return f'<input type="hidden" name="csrf_token" value="{token}">'


def validate_csrf() -> None:
    expected_token = session.get('_csrf_token', '')
    provided_token = (
        request.headers.get('X-CSRF-Token')
        or request.form.get('csrf_token')
        or request.headers.get('X-CSRFToken')
    )
    if not expected_token or not provided_token or not hmac.compare_digest(expected_token, provided_token):
        raise BadRequest('Invalid CSRF token.')


def should_validate_csrf() -> bool:
    if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        return False
    return request.path.startswith('/admin')


def _decode_basic_auth_header(header_value: str) -> tuple[str, str] | None:
    if not header_value or not header_value.startswith('Basic '):
        return None
    try:
        encoded = header_value.split(' ', 1)[1]
        decoded = base64.b64decode(encoded).decode('utf-8')
    except Exception:
        return None
    if ':' not in decoded:
        return None
    username, password = decoded.split(':', 1)
    return username, password


def _ip_matches_allowed_list(client_ip: str, allowed_values: Iterable[str]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for allowed_value in allowed_values:
        try:
            if '/' in allowed_value:
                if ip_obj in ipaddress.ip_network(allowed_value, strict=False):
                    return True
            elif ip_obj == ipaddress.ip_address(allowed_value):
                return True
        except ValueError:
            continue
    return False


def enforce_admin_access_controls() -> None:
    if not request.path.startswith('/admin'):
        return

    allowed_ips = current_app.config.get('ADMIN_ALLOWED_IPS') or ()
    client_ip = get_request_ip()
    if allowed_ips and not _ip_matches_allowed_list(client_ip, allowed_ips):
        current_app.logger.warning('Blocked admin request from disallowed IP %s', client_ip)
        abort(403)

    configured_user = current_app.config.get('ADMIN_BASIC_AUTH_USERNAME', '')
    configured_password = current_app.config.get('ADMIN_BASIC_AUTH_PASSWORD', '')
    if not configured_user or not configured_password:
        return

    credentials = _decode_basic_auth_header(request.headers.get('Authorization', ''))
    if not credentials:
        abort(401, www_authenticate='Basic realm="Hotel-102 Admin"')

    username, password = credentials
    if not (
        hmac.compare_digest(username, configured_user)
        and hmac.compare_digest(password, configured_password)
    ):
        current_app.logger.warning('Blocked admin request with invalid basic auth from IP %s', client_ip)
        abort(401, www_authenticate='Basic realm="Hotel-102 Admin"')


def register_security_context(app):
    @app.context_processor
    def inject_security_helpers():
        return {
            'csrf_token': generate_csrf_token,
            'csrf_input': csrf_input_html,
        }


def apply_security_headers(response):
    if not current_app.config.get('SECURITY_HEADERS_ENABLED', True):
        return response

    csp = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "media-src 'self' https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers.setdefault('Content-Security-Policy', csp)
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    if request_is_secure():
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response


def check_login_rate_limit(username: str) -> int | None:
    max_attempts = current_app.config.get('ADMIN_RATE_LIMIT_ATTEMPTS', 5)
    window_seconds = current_app.config.get('ADMIN_RATE_LIMIT_WINDOW_SECONDS', 900)
    key = f'{get_request_ip()}::{(username or "").strip().lower()}'
    now = time.time()
    attempts = _login_attempts[key]
    while attempts and now - attempts[0] > window_seconds:
        attempts.popleft()
    if len(attempts) >= max_attempts:
        retry_after = int(window_seconds - (now - attempts[0]))
        return max(retry_after, 1)
    return None


def register_failed_login_attempt(username: str) -> None:
    key = f'{get_request_ip()}::{(username or "").strip().lower()}'
    attempts = _login_attempts[key]
    attempts.append(time.time())


def clear_login_rate_limit(username: str) -> None:
    key = f'{get_request_ip()}::{(username or "").strip().lower()}'
    _login_attempts.pop(key, None)
