from __future__ import annotations

from booking_app.services.iyzico_client import IyzicoCheckoutFormClient
from booking_app.services.pricing import build_special_requests_text, format_price
from core.models import Reservation, db


class PaymentCallbackError(RuntimeError):
    pass


def map_payment_status(response):
    service_status = str(response.get('status', '')).lower()
    if service_status != 'success':
        return 'FAILED'

    payment_status = str(response.get('paymentStatus', '')).upper()
    if payment_status in {'SUCCESS', 'PAID'}:
        return 'PAID'
    if payment_status in {'FAILURE', 'FAILED'}:
        return 'FAILED'
    return 'PENDING'


def create_reservation_from_paid_draft(store, booking_draft_id):
    draft = store.get(booking_draft_id)
    if not draft:
        raise PaymentCallbackError('Booking draft was not found.')
    if draft.get('reservation_id'):
        return draft['reservation_id']

    primary_guest = draft['details'].get('primaryGuest') if isinstance(draft['details'].get('primaryGuest'), dict) else {}
    guest_name = f'{primary_guest.get("firstName", "")} {primary_guest.get("lastName", "")}'.strip()
    guest_email = primary_guest.get('email') or draft['payment_state'].get('billingEmail') or ''
    guest_phone = primary_guest.get('phone') or ''

    reservation = Reservation(
        check_in=draft['stay']['checkIn'],
        check_out=draft['stay']['checkOut'],
        adults=draft['stay']['adults'],
        children=draft['stay']['children'],
        room_id=draft['room']['id'],
        room_count=draft['room']['roomCount'],
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        special_requests=build_special_requests_text(draft['details']),
        total_price=format_price(draft['pricing_snapshot']['total'], draft['pricing_snapshot'].get('currencySymbol', '$')),
        status='Confirmed',
    )
    db.session.add(reservation)
    db.session.commit()
    store.set_reservation_id(booking_draft_id, reservation.id)
    return reservation.id


def retrieve_checkout_result_for_draft(store, booking_draft_id, token):
    draft = store.get(booking_draft_id)
    if not draft:
        raise PaymentCallbackError('Booking draft was not found.')
    if not token:
        raise PaymentCallbackError('iyzico callback token is missing.')

    client = IyzicoCheckoutFormClient.from_env()
    response = client.retrieve_checkout_form({
        'locale': 'en',
        'conversationId': booking_draft_id,
        'token': token,
    })
    mapped_status = map_payment_status(response)
    error_message = response.get('errorMessage') if mapped_status != 'PAID' else None
    updated_draft = store.mark_payment_result(
        booking_draft_id=booking_draft_id,
        mapped_status=mapped_status,
        raw_response=response,
        error_message=error_message,
    )
    if not updated_draft:
        raise PaymentCallbackError('Booking draft could not be updated after callback retrieval.')

    if mapped_status == 'PAID':
        create_reservation_from_paid_draft(store, booking_draft_id)

    return store.get(booking_draft_id)
