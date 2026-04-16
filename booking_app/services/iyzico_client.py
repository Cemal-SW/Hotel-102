from __future__ import annotations

import json
import os

import iyzipay


SANDBOX_BASE_URL = 'sandbox-api.iyzipay.com'
LIVE_BASE_URL = 'api.iyzipay.com'


class IyzicoConfigurationError(RuntimeError):
    pass


def _load_json_response(result):
    if hasattr(result, 'read'):
        raw = result.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return json.loads(raw)
    if isinstance(result, str):
        return json.loads(result)
    return json.loads(str(result))


class IyzicoCheckoutFormClient:
    def __init__(self, api_key, secret_key, base_url=SANDBOX_BASE_URL, locale='en'):
        self.options = {
            'api_key': api_key,
            'secret_key': secret_key,
            'base_url': base_url,
        }
        self.locale = locale

    @classmethod
    def from_env(cls):
        api_key = os.environ.get('IYZICO_API_KEY')
        secret_key = os.environ.get('IYZICO_SECRET_KEY')
        mode = os.environ.get('IYZICO_MODE', 'sandbox').strip().lower() or 'sandbox'
        default_base_url = LIVE_BASE_URL if mode == 'live' else SANDBOX_BASE_URL
        base_url = os.environ.get('IYZICO_BASE_URL', default_base_url).strip() or default_base_url
        if not api_key or not secret_key:
            raise IyzicoConfigurationError('IYZICO credentials are missing on the backend.')
        if mode not in {'sandbox', 'live'}:
            raise IyzicoConfigurationError('IYZICO_MODE must be either "sandbox" or "live".')
        if mode == 'sandbox' and base_url != SANDBOX_BASE_URL:
            raise IyzicoConfigurationError('Sandbox mode must use the sandbox iyzico base URL.')
        if mode == 'live' and base_url != LIVE_BASE_URL:
            raise IyzicoConfigurationError('Live mode must use the live iyzico base URL.')
        return cls(api_key=api_key, secret_key=secret_key, base_url=base_url)

    def initialize_checkout_form(self, payload):
        response = iyzipay.CheckoutFormInitialize().create(payload, self.options)
        return _load_json_response(response)

    def retrieve_checkout_form(self, payload):
        response = iyzipay.CheckoutForm().retrieve(payload, self.options)
        return _load_json_response(response)
