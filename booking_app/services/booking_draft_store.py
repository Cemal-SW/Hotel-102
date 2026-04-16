from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from core.models import BookingDraft, db


def utc_now_iso():
    return datetime.now(UTC).isoformat()


def build_default_payment_state(payment):
    payment_payload = payment if isinstance(payment, dict) else {}
    return {
        'provider': 'iyzico',
        'mode': 'sandbox',
        'status': 'PENDING',
        'phase': 'drafted',
        'selectedMethod': payment_payload.get('method') or 'card_hold',
        'billingName': payment_payload.get('billingName') or '',
        'billingEmail': payment_payload.get('billingEmail') or '',
        'agreedToTerms': bool(payment_payload.get('agreedToTerms')),
        'checkoutForm': {
            'token': None,
            'paymentPageUrl': None,
            'initializedAt': None,
            'retrievedAt': None,
            'rawInitializeResponse': None,
            'rawRetrieveResponse': None,
        },
        'result': {
            'paymentId': None,
            'paidPrice': None,
            'currency': None,
            'basketId': None,
            'conversationId': None,
        },
        'lastError': None,
        'events': [],
    }


class InMemoryBookingDraftStore:
    def __init__(self):
        pass

    @staticmethod
    def _serialize(record):
        draft = json.loads(record.payload_json)
        draft['publicToken'] = record.public_token
        return draft

    @staticmethod
    def _save_record(record, draft):
        record.payload_json = json.dumps(draft)
        record.checkout_token = draft.get('payment_state', {}).get('checkoutForm', {}).get('token')
        db.session.add(record)
        db.session.commit()
        return deepcopy(draft)

    def create_or_update(self, payload, booking_draft_id=None):
        now = utc_now_iso()
        record = db.session.get(BookingDraft, booking_draft_id) if booking_draft_id else None
        existing = self._serialize(record) if record else None
        draft_id = booking_draft_id or uuid4().hex
        public_token = record.public_token if record else uuid4().hex
        payment_state = deepcopy(existing['payment_state']) if existing else build_default_payment_state(payload.get('payment'))
        payment_payload = payload.get('payment') if isinstance(payload.get('payment'), dict) else {}
        payment_state['selectedMethod'] = payment_payload.get('method') or payment_state.get('selectedMethod') or 'card_hold'
        payment_state['billingName'] = payment_payload.get('billingName') or ''
        payment_state['billingEmail'] = payment_payload.get('billingEmail') or ''
        payment_state['agreedToTerms'] = bool(payment_payload.get('agreedToTerms'))
        payment_state['events'].append({
            'type': 'draft.updated' if existing else 'draft.created',
            'status': payment_state['status'],
            'at': now,
        })

        draft = {
            'id': draft_id,
            'publicToken': public_token,
            'stay': deepcopy(payload.get('stay') or {}),
            'room': deepcopy(payload.get('room') or {}),
            'details': deepcopy(payload.get('details') or {}),
            'pricing_snapshot': deepcopy(payload.get('pricing_snapshot') or {}),
            'payment_state': payment_state,
            'reservation_id': existing.get('reservation_id') if existing else None,
            'created_at': existing.get('created_at') if existing else now,
            'updated_at': now,
        }
        if not record:
            record = BookingDraft(id=draft_id, public_token=public_token, payload_json='')
        return self._save_record(record, draft)

    def get(self, booking_draft_id):
        record = db.session.get(BookingDraft, booking_draft_id)
        return deepcopy(self._serialize(record)) if record else None

    def get_by_token(self, token):
        record = BookingDraft.query.filter_by(checkout_token=token).first()
        return deepcopy(self._serialize(record)) if record else None

    def get_by_public_token(self, public_token):
        record = BookingDraft.query.filter_by(public_token=public_token).first()
        return deepcopy(self._serialize(record)) if record else None

    def mark_payment_initialized(self, booking_draft_id, token, payment_page_url, raw_response):
        record = db.session.get(BookingDraft, booking_draft_id)
        if not record:
            return None

        draft = self._serialize(record)
        payment_state = draft['payment_state']
        payment_state['status'] = 'PENDING'
        payment_state['phase'] = 'checkout_form_initialized'
        payment_state['lastError'] = None
        payment_state['checkoutForm']['token'] = token
        payment_state['checkoutForm']['paymentPageUrl'] = payment_page_url
        payment_state['checkoutForm']['initializedAt'] = utc_now_iso()
        payment_state['checkoutForm']['rawInitializeResponse'] = deepcopy(raw_response)
        payment_state['events'].append({
            'type': 'payment.initialize',
            'status': 'PENDING',
            'token': token,
            'at': utc_now_iso(),
        })
        draft['updated_at'] = utc_now_iso()
        return self._save_record(record, draft)

    def mark_payment_result(self, booking_draft_id, mapped_status, raw_response, error_message=None):
        record = db.session.get(BookingDraft, booking_draft_id)
        if not record:
            return None

        draft = self._serialize(record)
        payment_state = draft['payment_state']
        payment_state['status'] = mapped_status
        payment_state['phase'] = 'checkout_form_retrieved'
        payment_state['lastError'] = error_message
        payment_state['checkoutForm']['retrievedAt'] = utc_now_iso()
        payment_state['checkoutForm']['rawRetrieveResponse'] = deepcopy(raw_response)
        payment_state['result'] = {
            'paymentId': raw_response.get('paymentId'),
            'paidPrice': raw_response.get('paidPrice'),
            'currency': raw_response.get('currency'),
            'basketId': raw_response.get('basketId'),
            'conversationId': raw_response.get('conversationId'),
        }
        payment_state['events'].append({
            'type': 'payment.retrieve',
            'status': mapped_status,
            'at': utc_now_iso(),
            'paymentId': raw_response.get('paymentId'),
        })
        draft['updated_at'] = utc_now_iso()
        return self._save_record(record, draft)

    def set_reservation_id(self, booking_draft_id, reservation_id):
        record = db.session.get(BookingDraft, booking_draft_id)
        if not record:
            return None

        draft = self._serialize(record)
        draft['reservation_id'] = reservation_id
        draft['payment_state']['events'].append({
            'type': 'reservation.created',
            'status': draft['payment_state']['status'],
            'at': utc_now_iso(),
            'reservationId': reservation_id,
        })
        draft['updated_at'] = utc_now_iso()
        return self._save_record(record, draft)
