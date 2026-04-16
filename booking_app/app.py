import os
import subprocess
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from core.models import db, Room, Reservation, initialize_database
from core.config import BaseConfig
from core.security import apply_security_headers, enforce_https_redirect, get_request_ip
from core.uploads import is_public_upload
from booking_app.services.booking_draft_store import InMemoryBookingDraftStore
from booking_app.services.iyzico_client import IyzicoConfigurationError
from booking_app.services.payment_callback import PaymentCallbackError, retrieve_checkout_result_for_draft
from booking_app.services.payment_initialize import PaymentInitializationError, initialize_checkout_form_for_draft
from booking_app.services.pricing import (
    PricingValidationError,
    build_priced_booking_draft,
    build_special_requests_text,
    format_price,
    get_enhancement_total,
    parse_date,
    parse_price,
)

app = Flask(__name__)
app.config.from_object(BaseConfig)

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # Root dir

db.init_app(app)
app.jinja_env.auto_reload = True

with app.app_context():
    initialize_database()

MAIN_URL = app.config['MAIN_URL']
BOOKING_PUBLIC_URL = app.config['BOOKING_PUBLIC_URL']
booking_draft_store = InMemoryBookingDraftStore()


def ensure_booking_css():
    if not (app.debug or app.config.get('BUILD_BOOKING_CSS_ON_REQUEST', False)):
        return

    src_path = Path(basedir) / 'booking_app' / 'static' / 'booking.src.css'
    output_path = Path(basedir) / 'booking_app' / 'static' / 'booking.css'

    if not src_path.exists():
        return

    if output_path.exists() and output_path.stat().st_mtime >= src_path.stat().st_mtime:
        return

    try:
        subprocess.run(
            [
                'npx',
                '@tailwindcss/cli',
                '-i',
                str(src_path),
                '-o',
                str(output_path),
                '--minify',
            ],
            cwd=basedir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        app.logger.exception('Booking CSS rebuild failed')


def get_booking_asset_version():
    assets = [
        Path(basedir) / 'booking_app' / 'templates' / 'booking.html',
        Path(basedir) / 'booking_app' / 'templates' / 'stay.html',
        Path(basedir) / 'booking_app' / 'templates' / 'room.html',
        Path(basedir) / 'booking_app' / 'templates' / 'details.html',
        Path(basedir) / 'booking_app' / 'templates' / 'payment.html',
        Path(basedir) / 'booking_app' / 'templates' / 'success.html',
        Path(basedir) / 'booking_app' / 'static' / 'booking.js',
        Path(basedir) / 'booking_app' / 'static' / 'booking.css',
        Path(basedir) / 'booking_app' / 'static' / 'booking.src.css',
    ]

    mtimes = [int(path.stat().st_mtime) for path in assets if path.exists()]
    return max(mtimes) if mtimes else 0

@app.context_processor
def inject_globals():
    return dict(
        MAIN_URL=MAIN_URL,
        BOOKING_ASSET_VERSION=get_booking_asset_version(),
        BOOKING_BASE_PATH=(request.script_root or '').rstrip('/'),
    )


@app.before_request
def booking_before_request():
    https_redirect = enforce_https_redirect()
    if https_redirect is not None:
        return https_redirect


@app.after_request
def disable_response_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return apply_security_headers(response)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(basedir, 'data', 'uploads')
    if not is_public_upload(filename, allowed_extensions=set(app.config['PUBLIC_UPLOAD_EXTENSIONS'])):
        return {"success": False, "error": 'File not found.'}, 404
    return send_from_directory(upload_folder, filename)

@app.route('/')
def booking():
    ensure_booking_css()
    rooms = Room.query.order_by(Room.order_index).all()
    for room in rooms:
        apply_room_booking_metadata(room)
    return render_template('booking.html', rooms=rooms)


@app.route('/api/booking-version')
def booking_version():
    ensure_booking_css()
    return jsonify({'version': get_booking_asset_version()})


@app.route('/api/room-availability')
def room_availability():
    try:
        check_in = request.args.get('checkIn')
        check_out = request.args.get('checkOut')
        check_in_date = parse_date(check_in, 'check-in date')
        check_out_date = parse_date(check_out, 'check-out date')

        if check_out_date <= check_in_date:
            return bad_request('Check-out date must be after check-in date.')

        rooms = Room.query.order_by(Room.order_index).all()
        payload = []
        for room in rooms:
            metadata = apply_room_booking_metadata(room, check_in_date, check_out_date)
            payload.append({
                'roomId': room.id,
                'available': metadata['available'],
                'quantityAvailable': metadata['quantityAvailable'],
                'availabilityStatus': metadata['availabilityStatus'],
            })

        return jsonify({'success': True, 'rooms': payload})
    except ValueError as exc:
        return bad_request(str(exc))

def bad_request(message):
    return {"success": False, "error": message}, 400


def get_public_booking_url():
    if BOOKING_PUBLIC_URL:
        return BOOKING_PUBLIC_URL.rstrip('/')
    return f"{request.host_url.rstrip('/')}{request.script_root or ''}".rstrip('/')


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
        legacy_capacity + max_children_default
    )

    base_adults = max(1, coerce_int(get_room_attr(room, 'base_adults', 'baseAdults'), legacy_capacity))
    base_children = max(0, coerce_int(get_room_attr(room, 'base_children', 'baseChildren'), base_children_default))
    max_adults = max(base_adults, coerce_int(get_room_attr(room, 'max_adults', 'maxAdults'), base_adults))
    allows_extra_bed = coerce_bool(get_room_attr(room, 'allows_extra_bed', 'allowsExtraBed'), allows_extra_bed_default)
    max_children = max(
        base_children,
        coerce_int(get_room_attr(room, 'max_children', 'maxChildren'), base_children + (1 if allows_extra_bed else 0))
    )
    max_occupancy = max(
        max_adults,
        base_adults + base_children,
        coerce_int(get_room_attr(room, 'max_occupancy', 'maxOccupancy'), max_occupancy_default)
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

def has_overlapping_reservation(room_id, check_in_date, check_out_date):
    reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status != 'Cancelled'
    ).all()

    for existing in reservations:
        try:
            existing_check_in = parse_date(existing.check_in, 'existing check-in date')
            existing_check_out = parse_date(existing.check_out, 'existing check-out date')
        except ValueError:
            continue

        overlaps = check_in_date < existing_check_out and check_out_date > existing_check_in
        if overlaps:
            return True

    return False


def get_overlapping_reservation_count(room_id, check_in_date, check_out_date):
    reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status != 'Cancelled'
    ).all()
    overlap_count = 0

    for existing in reservations:
        try:
            existing_check_in = parse_date(existing.check_in, 'existing check-in date')
            existing_check_out = parse_date(existing.check_out, 'existing check-out date')
        except ValueError:
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


def apply_room_booking_metadata(room, check_in_date=None, check_out_date=None):
    metadata = build_room_availability(room, check_in_date, check_out_date)
    room.booking_capacity = metadata['legacyCapacity']
    room.booking_base_adults = metadata['baseAdults']
    room.booking_base_children = metadata['baseChildren']
    room.booking_max_adults = metadata['maxAdults']
    room.booking_max_children = metadata['maxChildren']
    room.booking_max_occupancy = metadata['maxOccupancy']
    room.booking_allows_extra_bed = metadata['allowsExtraBed']
    room.booking_available = metadata['available']
    room.booking_quantity_available = metadata['quantityAvailable']
    room.booking_availability_status = metadata['availabilityStatus']
    return metadata


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


def evaluate_room_for_party(room_or_metadata, adults, children):
    metadata = room_or_metadata if isinstance(room_or_metadata, dict) else build_room_availability(room_or_metadata)
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
        reason = (
            f'{multi_room["requiredRoomCount"]} rooms required, only {metadata["quantityAvailable"]} available.'
        )
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


@app.route('/api/booking-drafts', methods=['POST'])
def api_create_booking_draft():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return bad_request('Request body must be valid JSON.')

        draft_source = data.get('draft') if isinstance(data.get('draft'), dict) else data
        booking_draft_id = data.get('bookingDraftId')
        priced_draft = build_priced_booking_draft(draft_source)
        stored_draft = booking_draft_store.create_or_update(
            priced_draft,
            booking_draft_id=booking_draft_id,
        )
        return jsonify({
            'success': True,
            'bookingDraftId': stored_draft['id'],
            'publicToken': stored_draft.get('publicToken'),
            'pricingSnapshot': stored_draft['pricing_snapshot'],
            'paymentState': {
                'status': stored_draft['payment_state'].get('status', 'PENDING'),
            },
        })
    except PricingValidationError as exc:
        return bad_request(str(exc))
    except Exception:
        app.logger.exception('Booking draft creation failed')
        return {"success": False, "error": 'Booking draft could not be created.'}, 500


@app.route('/api/payments/iyzico/initialize', methods=['POST'])
def api_initialize_iyzico_checkout():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return bad_request('Request body must be valid JSON.')

        booking_draft_id = str(data.get('bookingDraftId') or '').strip()
        if not booking_draft_id:
            return bad_request('bookingDraftId is required.')

        updated_draft = initialize_checkout_form_for_draft(
            store=booking_draft_store,
            booking_draft_id=booking_draft_id,
            public_booking_base_url=get_public_booking_url(),
            customer_ip=get_request_ip(),
        )
        checkout_form = updated_draft['payment_state']['checkoutForm']
        return jsonify({
            'success': True,
            'bookingDraftId': booking_draft_id,
            'publicToken': updated_draft.get('publicToken'),
            'paymentPageUrl': checkout_form['paymentPageUrl'],
            'paymentState': {
                'status': updated_draft['payment_state'].get('status', 'PENDING'),
            },
        })
    except PricingValidationError as exc:
        return bad_request(str(exc))
    except (PaymentInitializationError, IyzicoConfigurationError) as exc:
        return {"success": False, "error": str(exc)}, 500
    except Exception:
        app.logger.exception('iyzico checkout initialization failed')
        return {"success": False, "error": 'iyzico checkout could not be initialized.'}, 500


@app.route('/payment/iyzico/callback', methods=['GET', 'POST'])
def iyzico_checkout_callback():
    booking_draft_id = str(request.args.get('bookingDraftId') or '').strip()
    token = str(request.values.get('token') or '').strip()

    if not booking_draft_id and token:
        draft_from_token = booking_draft_store.get_by_token(token)
        booking_draft_id = draft_from_token['id'] if draft_from_token else ''

    if not booking_draft_id:
        return bad_request('bookingDraftId is required for callback handling.')

    try:
        retrieve_checkout_result_for_draft(
            store=booking_draft_store,
            booking_draft_id=booking_draft_id,
            token=token,
        )
    except (PaymentCallbackError, IyzicoConfigurationError) as exc:
        booking_draft_store.mark_payment_result(
            booking_draft_id=booking_draft_id,
            mapped_status='FAILED',
            raw_response={
                'status': 'failure',
                'errorMessage': str(exc),
                'token': token,
            },
            error_message=str(exc),
        )
    except Exception:
        app.logger.exception('iyzico callback handling failed')
        booking_draft_store.mark_payment_result(
            booking_draft_id=booking_draft_id,
            mapped_status='FAILED',
            raw_response={
                'status': 'failure',
                'errorMessage': 'Unexpected callback failure.',
                'token': token,
            },
            error_message='Unexpected callback failure.',
        )

    final_draft = booking_draft_store.get(booking_draft_id)
    status_token = final_draft.get('publicToken') if final_draft else ''
    return redirect(url_for('booking', step=5, statusToken=status_token))


@app.route('/api/booking-drafts/status/<public_token>')
def api_booking_draft_approval_status(public_token):
    draft = booking_draft_store.get_by_public_token(public_token)
    if not draft:
        return {"success": False, "error": 'Booking draft not found.'}, 404

    return jsonify({
        'success': True,
        'publicToken': draft.get('publicToken'),
        'paymentStatus': draft['payment_state']['status'],
        'pricingSnapshot': {
            'formattedTotal': draft['pricing_snapshot'].get('formattedTotal') or format_price(
                draft['pricing_snapshot'].get('total', 0),
                draft['pricing_snapshot'].get('currencySymbol', '$'),
            ),
        },
        'reservationId': draft.get('reservation_id'),
        'roomName': draft['room'].get('name'),
        'roomCount': draft['room'].get('roomCount'),
    })

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    return {
        "success": False,
        "error": 'Direct reservation creation is disabled. Complete the hosted payment flow instead.'
    }, 410

if __name__ == '__main__':
    app.run(debug=app.debug, port=5001)
