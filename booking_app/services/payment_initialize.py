from __future__ import annotations

from datetime import UTC, datetime

from booking_app.services.iyzico_client import IyzicoCheckoutFormClient
from booking_app.services.pricing import (
    build_priced_booking_draft,
    format_decimal,
    normalize_phone,
)


class PaymentInitializationError(RuntimeError):
    pass


def split_name(full_name):
    parts = [part for part in str(full_name or '').strip().split() if part]
    if not parts:
        return 'Guest', 'Guest'
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], ' '.join(parts[1:])


def sanitize_identity_number(value):
    cleaned = ''.join(ch for ch in str(value or '') if ch.isalnum())
    return cleaned[:32] if cleaned else '11111111111'


def build_callback_url(public_booking_base_url, booking_draft_id):
    base = public_booking_base_url.rstrip('/')
    return f'{base}/payment/iyzico/callback'


def build_checkout_form_request(draft, public_booking_base_url, customer_ip):
    booking_draft_id = draft['id']
    primary_guest = draft['details'].get('primaryGuest') if isinstance(draft['details'].get('primaryGuest'), dict) else {}
    adult_guests = draft['details'].get('adultGuests') if isinstance(draft['details'].get('adultGuests'), list) else []
    lead_occupant = adult_guests[0] if adult_guests and isinstance(adult_guests[0], dict) else {}
    full_name = f'{primary_guest.get("firstName", "")} {primary_guest.get("lastName", "")}'.strip()
    first_name, last_name = split_name(full_name)
    contact_name = f'{first_name} {last_name}'.strip()
    fallback_address = 'Hotel-102 sandbox checkout placeholder address'
    now = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
    address = {
        'contactName': contact_name or 'Guest Guest',
        'city': 'Istanbul',
        'country': 'Turkey',
        'address': fallback_address,
        'zipCode': '34000',
    }

    return {
        'locale': 'en',
        'conversationId': booking_draft_id,
        'price': format_decimal(draft['pricing_snapshot']['total']),
        'paidPrice': format_decimal(draft['pricing_snapshot']['total']),
        'currency': draft['pricing_snapshot']['currency'],
        'basketId': booking_draft_id,
        'paymentGroup': 'PRODUCT',
        'paymentChannel': 'WEB',
        'callbackUrl': build_callback_url(public_booking_base_url, booking_draft_id),
        'buyer': {
            'id': booking_draft_id,
            'name': first_name,
            'surname': last_name,
            'gsmNumber': normalize_phone(primary_guest.get('phone')),
            'email': primary_guest.get('email') or draft['payment_state'].get('billingEmail') or 'sandbox@example.com',
            'identityNumber': sanitize_identity_number(lead_occupant.get('passportOrId')),
            'lastLoginDate': now,
            'registrationDate': now,
            'registrationAddress': fallback_address,
            'ip': customer_ip or '127.0.0.1',
            'city': 'Istanbul',
            'country': 'Turkey',
            'zipCode': '34000',
        },
        'shippingAddress': address,
        'billingAddress': address,
        'basketItems': draft['pricing_snapshot']['basketItems'],
    }


def initialize_checkout_form_for_draft(store, booking_draft_id, public_booking_base_url, customer_ip):
    existing_draft = store.get(booking_draft_id)
    if not existing_draft:
        raise PaymentInitializationError('Booking draft was not found.')

    refreshed_draft_payload = build_priced_booking_draft(existing_draft)
    draft = store.create_or_update(refreshed_draft_payload, booking_draft_id=booking_draft_id)
    client = IyzicoCheckoutFormClient.from_env()
    checkout_request = build_checkout_form_request(draft, public_booking_base_url, customer_ip)
    response = client.initialize_checkout_form(checkout_request)
    if str(response.get('status', '')).lower() != 'success':
        raise PaymentInitializationError(response.get('errorMessage') or 'iyzico checkout form initialization failed.')

    token = response.get('token')
    payment_page_url = response.get('paymentPageUrl')
    if not token or not payment_page_url:
        raise PaymentInitializationError('iyzico did not return a checkout token or payment page URL.')

    updated_draft = store.mark_payment_initialized(
        booking_draft_id=booking_draft_id,
        token=token,
        payment_page_url=payment_page_url,
        raw_response=response,
    )
    if not updated_draft:
        raise PaymentInitializationError('Booking draft could not be updated after iyzico initialization.')
    return updated_draft
