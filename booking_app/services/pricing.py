from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from core.models import Room, Reservation


DEFAULT_CURRENCY = 'USD'
DEFAULT_CURRENCY_SYMBOL = '$'
ENHANCEMENT_PRICES = {
    'airportTransfer': 85,
    'spaTreatment': 150,
    'lateCheckout': 50,
}
ENHANCEMENT_LABELS = {
    'airportTransfer': 'Airport Transfer',
    'spaTreatment': 'Spa Treatment',
    'lateCheckout': 'Late Check-out',
}


class PricingValidationError(ValueError):
    pass


def parse_date(value, field_name):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError) as exc:
        raise PricingValidationError(f'Invalid {field_name}. Use YYYY-MM-DD format.') from exc


def parse_price(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        raise PricingValidationError('Selected room price is invalid.')
    return int(digits)


def format_price(value, currency_symbol=DEFAULT_CURRENCY_SYMBOL):
    return f'{currency_symbol}{int(value):,}'


def format_decimal(value):
    amount = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return format(amount, 'f')


def normalize_phone(value):
    raw = str(value or '').strip()
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return '+905555555555'
    if raw.startswith('+'):
        return f'+{digits}'
    if raw.startswith('00'):
        return f'+{digits[2:]}'
    return f'+{digits}'


def coerce_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off'}:
        return False
    return default


def get_room_attr(room, *names):
    for name in names:
        if hasattr(room, name):
            value = getattr(room, name)
            if value is not None:
                return value
    return None


def infer_room_bedrooms(bed_value):
    label = (bed_value or '').lower()
    if 'studio' in label:
        return 0

    digits = ''.join(ch for ch in label if ch.isdigit())
    if digits:
        return max(1, int(digits))

    return 1


def infer_room_capacity(bed_value):
    label = (bed_value or '').lower()
    if 'studio' in label:
        return 2

    digits = ''.join(ch for ch in label if ch.isdigit())
    if digits:
        return max(2, int(digits) * 2)

    return 2


def build_room_booking_profile(room):
    legacy_capacity = max(1, coerce_int(get_room_attr(room, 'booking_capacity', 'capacity'), infer_room_capacity(room.bed)))
    bedrooms = infer_room_bedrooms(room.bed)
    allows_extra_bed_default = bedrooms >= 1
    base_children_default = 0 if bedrooms == 0 else min(2, bedrooms)
    max_children_default = base_children_default + (1 if allows_extra_bed_default else 0)
    max_occupancy_default = min(
        legacy_capacity + (2 if allows_extra_bed_default else 0),
        legacy_capacity + max_children_default,
    )

    base_adults = max(1, coerce_int(get_room_attr(room, 'base_adults', 'baseAdults'), legacy_capacity))
    base_children = max(0, coerce_int(get_room_attr(room, 'base_children', 'baseChildren'), base_children_default))
    max_adults = max(base_adults, coerce_int(get_room_attr(room, 'max_adults', 'maxAdults'), base_adults))
    allows_extra_bed = coerce_bool(get_room_attr(room, 'allows_extra_bed', 'allowsExtraBed'), allows_extra_bed_default)
    max_children = max(
        base_children,
        coerce_int(get_room_attr(room, 'max_children', 'maxChildren'), base_children + (1 if allows_extra_bed else 0)),
    )
    max_occupancy = max(
        max_adults,
        base_adults + base_children,
        coerce_int(get_room_attr(room, 'max_occupancy', 'maxOccupancy'), max_occupancy_default),
    )
    inventory_total = max(
        0,
        coerce_int(
            get_room_attr(
                room,
                'inventory_total',
                'inventory',
                'quantity_total',
                'quantity',
                'quantity_available',
                'quantityAvailable',
            ),
            1,
        ),
    )
    admin_available = coerce_bool(get_room_attr(room, 'available', 'is_available', 'isAvailable'), True)

    return {
        'legacyCapacity': legacy_capacity,
        'baseAdults': base_adults,
        'baseChildren': base_children,
        'maxAdults': max_adults,
        'maxChildren': max_children,
        'maxOccupancy': max_occupancy,
        'allowsExtraBed': allows_extra_bed,
        'inventoryTotal': inventory_total,
        'adminAvailable': admin_available,
    }


def get_overlapping_reservation_count(room_id, check_in_date, check_out_date):
    reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status != 'Cancelled',
    ).all()
    overlap_count = 0

    for existing in reservations:
        try:
            existing_check_in = parse_date(existing.check_in, 'existing check-in date')
            existing_check_out = parse_date(existing.check_out, 'existing check-out date')
        except PricingValidationError:
            continue

        if check_in_date < existing_check_out and check_out_date > existing_check_in:
            overlap_count += max(1, coerce_int(getattr(existing, 'room_count', 1), 1))

    return overlap_count


def build_room_availability(room, check_in_date=None, check_out_date=None):
    profile = build_room_booking_profile(room)
    quantity_available = profile['inventoryTotal']

    if check_in_date and check_out_date:
        overlap_count = get_overlapping_reservation_count(room.id, check_in_date, check_out_date)
        quantity_available = max(0, profile['inventoryTotal'] - overlap_count)

    available = profile['adminAvailable'] and quantity_available > 0

    if not profile['adminAvailable']:
        availability_status = 'Currently unavailable'
    elif check_in_date and check_out_date and quantity_available <= 0:
        availability_status = 'Unavailable for selected dates'
    elif quantity_available > 1:
        availability_status = f'{quantity_available} rooms available'
    else:
        availability_status = 'Available'

    return {
        **profile,
        'available': available,
        'quantityAvailable': quantity_available,
        'availabilityStatus': availability_status,
    }


def evaluate_single_room(metadata, adults, children):
    adult_count = max(1, coerce_int(adults, 1))
    child_count = max(0, coerce_int(children, 0))
    total_guests = adult_count + child_count
    base_occupancy = max(1, metadata['baseAdults'] + metadata['baseChildren'])
    fits_adults = adult_count <= metadata['maxAdults']
    fits_children = child_count <= metadata['maxChildren']
    fits_total = total_guests <= metadata['maxOccupancy']
    single_room_suitable = fits_adults and fits_children and fits_total
    comfortable_fit = (
        adult_count <= metadata['baseAdults']
        and child_count <= metadata['baseChildren']
        and total_guests <= base_occupancy
    )
    fits_with_extra_bed = (
        metadata['allowsExtraBed']
        and single_room_suitable
        and (
            child_count > metadata['baseChildren']
            or total_guests > base_occupancy
        )
    )
    good_fit = single_room_suitable and not comfortable_fit and not fits_with_extra_bed

    return {
        'singleRoomSuitable': single_room_suitable,
        'comfortableFit': comfortable_fit,
        'goodFit': good_fit,
        'fitsWithExtraBed': fits_with_extra_bed,
        'fitsAdults': fits_adults,
        'fitsChildren': fits_children,
        'fitsTotal': fits_total,
    }


def evaluate_multi_room_option(metadata, adults, children):
    adult_count = max(1, coerce_int(adults, 1))
    child_count = max(0, coerce_int(children, 0))
    total_guests = adult_count + child_count
    if adult_count < 1:
        return {
            'multiRoomPossible': False,
            'requiredRoomCount': 0,
        }

    adults_based = max(1, metadata['maxAdults'])
    occupancy_based = max(1, metadata['maxOccupancy'])
    children_based = metadata['maxChildren']

    if child_count > 0 and children_based <= 0:
        return {
            'multiRoomPossible': False,
            'requiredRoomCount': 0,
        }

    required_room_count = max(
        (adult_count + adults_based - 1) // adults_based,
        (total_guests + occupancy_based - 1) // occupancy_based,
        ((child_count + children_based - 1) // children_based) if child_count > 0 else 1,
    )

    return {
        'multiRoomPossible': required_room_count > 1,
        'requiredRoomCount': required_room_count,
    }


def evaluate_room_for_party(metadata, adults, children):
    single_room = evaluate_single_room(metadata, adults, children)
    multi_room = evaluate_multi_room_option(metadata, adults, children)

    selectable = False
    recommended = False
    badge = 'Not suitable'
    reason = 'Not suitable as a single-room option.'
    score = 0

    if not metadata['available']:
        badge = 'Unavailable'
        reason = metadata['availabilityStatus']
        score = -1
    elif single_room['comfortableFit']:
        selectable = True
        recommended = True
        badge = 'Recommended'
        reason = 'Fits your group comfortably.'
        score = 100
    elif single_room['goodFit']:
        selectable = True
        badge = 'Good fit'
        reason = 'Good option for your selected guests.'
        score = 85
    elif single_room['fitsWithExtraBed']:
        selectable = True
        badge = 'Fits with extra bed'
        reason = 'Fits with extra bed.'
        score = 70
    elif multi_room['multiRoomPossible'] and multi_room['requiredRoomCount'] <= metadata['quantityAvailable']:
        selectable = True
        badge = 'Multi-room option'
        reason = f'{multi_room["requiredRoomCount"]} rooms needed for your group.'
        score = 75 - multi_room['requiredRoomCount']
    elif multi_room['multiRoomPossible']:
        badge = 'Limited availability'
        reason = f'{multi_room["requiredRoomCount"]} rooms required, only {metadata["quantityAvailable"]} available.'
        score = 20

    return {
        'singleRoomSuitable': single_room['singleRoomSuitable'],
        'multiRoomPossible': multi_room['multiRoomPossible'],
        'requiredRoomCount': 1 if single_room['singleRoomSuitable'] else multi_room['requiredRoomCount'],
        'selectable': selectable,
        'recommended': recommended,
        'score': score,
        'badge': badge,
        'reason': reason,
        'availabilityStatus': metadata['availabilityStatus'],
        'fitsAdults': single_room['fitsAdults'],
        'fitsChildren': single_room['fitsChildren'],
        'fitsTotal': single_room['fitsTotal'],
        'fitsWithExtraBed': single_room['fitsWithExtraBed'],
        'comfortableFit': single_room['comfortableFit'],
        'goodFit': single_room['goodFit'],
    }


def normalize_enhancements(enhancements):
    source = enhancements if isinstance(enhancements, dict) else {}
    return {
        key: bool(source.get(key))
        for key in ENHANCEMENT_PRICES
    }


def get_selected_enhancements(enhancements):
    normalized = normalize_enhancements(enhancements)
    return [
        {
            'key': key,
            'label': ENHANCEMENT_LABELS[key],
            'price': price,
        }
        for key, price in ENHANCEMENT_PRICES.items()
        if normalized.get(key)
    ]


def get_enhancement_total(enhancements):
    return sum(item['price'] for item in get_selected_enhancements(enhancements))


def build_special_requests_text(details):
    details_payload = details if isinstance(details, dict) else {}
    preferences = details_payload.get('preferences') if isinstance(details_payload.get('preferences'), dict) else {}
    parts = []

    if preferences.get('specialRequests'):
        parts.append(f'Special requests: {str(preferences.get("specialRequests")).strip()}')
    if preferences.get('arrivalTime'):
        parts.append(f'Arrival time: {str(preferences.get("arrivalTime")).strip()}')
    if preferences.get('bedPreference') and preferences.get('bedPreference') != 'no_preference':
        parts.append(f'Bed preference: {str(preferences.get("bedPreference")).strip()}')
    if preferences.get('smokingPreference') and preferences.get('smokingPreference') != 'no_preference':
        parts.append(f'Smoking preference: {str(preferences.get("smokingPreference")).strip()}')

    selected_enhancements = get_selected_enhancements(details_payload.get('enhancements'))
    if selected_enhancements:
        parts.append(
            'Enhancements: ' + ', '.join(item['label'] for item in selected_enhancements)
        )

    return ' | '.join(parts)


def _copy_guest_list(value):
    if not isinstance(value, list):
        return []
    return [deepcopy(item) for item in value if isinstance(item, dict)]


def build_priced_booking_draft(source):
    payload = source if isinstance(source, dict) else {}
    stay_source = payload.get('stay') if isinstance(payload.get('stay'), dict) else {}
    room_source = payload.get('room') if isinstance(payload.get('room'), dict) else {}
    details_source = payload.get('details') if isinstance(payload.get('details'), dict) else {}
    payment_source = payload.get('payment') if isinstance(payload.get('payment'), dict) else {}

    check_in = str(stay_source.get('checkIn') or '').strip()
    check_out = str(stay_source.get('checkOut') or '').strip()
    check_in_date = parse_date(check_in, 'check-in date')
    check_out_date = parse_date(check_out, 'check-out date')
    if check_out_date <= check_in_date:
        raise PricingValidationError('Check-out date must be after check-in date.')

    adults = max(1, coerce_int(stay_source.get('adults'), 1))
    children = max(0, coerce_int(stay_source.get('children'), 0))
    room_id = coerce_int(room_source.get('id'), 0)
    room_count = max(1, coerce_int(room_source.get('roomCount', room_source.get('room_count')), 1))

    room = db.session.get(Room, room_id)
    if room is None:
        raise PricingValidationError('Selected room does not exist.')

    room_metadata = build_room_availability(room, check_in_date, check_out_date)
    room_evaluation = evaluate_room_for_party(room_metadata, adults, children)
    if not room_evaluation['selectable']:
        raise PricingValidationError(room_evaluation['reason'])
    if room_count < room_evaluation['requiredRoomCount']:
        suffix = 's' if room_evaluation['requiredRoomCount'] != 1 else ''
        raise PricingValidationError(f'{room_evaluation["requiredRoomCount"]} room{suffix} are required for this stay.')
    if room_count > room_metadata['quantityAvailable']:
        suffix = 's' if room_metadata['quantityAvailable'] != 1 else ''
        raise PricingValidationError(f'Only {room_metadata["quantityAvailable"]} room{suffix} are available.')

    nights = (check_out_date - check_in_date).days
    nightly_rate = parse_price(room.price)
    selected_enhancements = get_selected_enhancements(details_source.get('enhancements'))
    enhancement_total = get_enhancement_total(details_source.get('enhancements'))
    room_total = nightly_rate * nights * room_count
    total = room_total + enhancement_total

    primary_guest = details_source.get('primaryGuest') if isinstance(details_source.get('primaryGuest'), dict) else {}
    normalized_details = {
        'primaryGuest': deepcopy(primary_guest),
        'adultGuests': _copy_guest_list(details_source.get('adultGuests')),
        'childGuests': _copy_guest_list(details_source.get('childGuests')),
        'preferences': deepcopy(details_source.get('preferences')) if isinstance(details_source.get('preferences'), dict) else {},
        'enhancements': normalize_enhancements(details_source.get('enhancements')),
        'usePrimaryGuestForAdult1': bool(details_source.get('usePrimaryGuestForAdult1')),
    }

    description = room_source.get('description') or room.short_desc or room.desc or ''
    image = room_source.get('image') or ''

    normalized_room = {
        'id': room.id,
        'name': room.name,
        'description': description,
        'image': image,
        'roomCount': room_count,
        'pricePerNight': nightly_rate,
        'availability': {
            'available': room_metadata['available'],
            'quantityAvailable': room_metadata['quantityAvailable'],
            'availabilityStatus': room_metadata['availabilityStatus'],
            'requiredRoomCount': room_evaluation['requiredRoomCount'],
        },
    }
    normalized_stay = {
        'checkIn': check_in,
        'checkOut': check_out,
        'nights': nights,
        'adults': adults,
        'children': children,
    }
    normalized_payment = {
        'method': str(payment_source.get('method') or 'card_hold'),
        'billingName': str(payment_source.get('billingName') or '').strip(),
        'billingEmail': str(payment_source.get('billingEmail') or '').strip(),
        'agreedToTerms': bool(payment_source.get('agreedToTerms')),
    }

    basket_items = [
        {
            'id': f'room-{room.id}',
            'name': room.name,
            'category1': 'Accommodation',
            'category2': 'Room',
            'itemType': 'PHYSICAL',
            'price': format_decimal(room_total),
        }
    ]
    basket_items.extend([
        {
            'id': f'enhancement-{item["key"]}',
            'name': item['label'],
            'category1': 'Enhancement',
            'category2': 'Service',
            'itemType': 'PHYSICAL',
            'price': format_decimal(item['price']),
        }
        for item in selected_enhancements
    ])

    pricing_snapshot = {
        'currency': DEFAULT_CURRENCY,
        'currencySymbol': DEFAULT_CURRENCY_SYMBOL,
        'nights': nights,
        'nightlyRate': nightly_rate,
        'roomTotal': room_total,
        'enhancementTotal': enhancement_total,
        'total': total,
        'formattedNightlyRate': format_price(nightly_rate),
        'formattedRoomTotal': format_price(room_total),
        'formattedEnhancementTotal': format_price(enhancement_total),
        'formattedTotal': format_price(total),
        'selectedEnhancements': selected_enhancements,
        'basketItems': basket_items,
    }

    return {
        'stay': normalized_stay,
        'room': normalized_room,
        'details': normalized_details,
        'payment': normalized_payment,
        'pricing_snapshot': pricing_snapshot,
    }
