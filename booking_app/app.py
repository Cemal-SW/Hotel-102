import os
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory
from core.models import db, Room, Reservation

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # Root dir
db_path = os.path.join(basedir, 'data', 'instance', 'hotel.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

db.init_app(app)
app.jinja_env.auto_reload = True

MAIN_URL = os.environ.get('MAIN_URL', 'http://127.0.0.1:5000/')
ENHANCEMENT_PRICES = {
    'airportTransfer': 85,
    'spaTreatment': 150,
    'lateCheckout': 50,
}


def ensure_booking_css():
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
    )


@app.after_request
def disable_response_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(basedir, 'data', 'uploads')
    return send_from_directory(upload_folder, filename)

@app.route('/')
def booking():
    ensure_booking_css()
    rooms = Room.query.order_by(Room.order_index).all()
    for room in rooms:
        room.booking_capacity = infer_room_capacity(room.bed)
    return render_template('booking.html', rooms=rooms)


@app.route('/api/booking-version')
def booking_version():
    ensure_booking_css()
    return jsonify({'version': get_booking_asset_version()})

def bad_request(message):
    return {"success": False, "error": message}, 400

def parse_price(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        raise ValueError('Selected room price is invalid.')
    return int(digits)

def format_price(value):
    return f'${value:,}'

def get_enhancement_total(enhancements):
    if not isinstance(enhancements, dict):
        return 0

    total = 0
    for key, price in ENHANCEMENT_PRICES.items():
        if enhancements.get(key):
            total += price
    return total

def infer_room_capacity(bed_value):
    label = (bed_value or '').lower()
    if 'studio' in label:
        return 2

    digits = ''.join(ch for ch in label if ch.isdigit())
    if digits:
        return max(2, int(digits) * 2)

    return 2

def parse_date(value, field_name):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f'Invalid {field_name}. Use YYYY-MM-DD format.')

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

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return bad_request('Request body must be valid JSON.')

        details = data.get('details') if isinstance(data.get('details'), dict) else {}
        primary_guest = details.get('primaryGuest') if isinstance(details.get('primaryGuest'), dict) else {}
        preferences = details.get('preferences') if isinstance(details.get('preferences'), dict) else {}
        enhancements = data.get('enhancements')
        if not isinstance(enhancements, dict):
            enhancements = details.get('enhancements') if isinstance(details.get('enhancements'), dict) else {}

        check_in = data.get('checkIn')
        check_out = data.get('checkOut')
        guest_name = (data.get('guestName') or '').strip()
        guest_email = (data.get('guestEmail') or '').strip()
        guest_phone = (data.get('guestPhone') or '').strip()
        special_requests = (data.get('specialRequests') or '').strip()
        total_price = str(data.get('totalPrice') or '0').strip()

        if not guest_name:
            first_name = (primary_guest.get('firstName') or '').strip()
            last_name = (primary_guest.get('lastName') or '').strip()
            guest_name = ' '.join(part for part in [first_name, last_name] if part).strip()

        if not guest_email:
            guest_email = (primary_guest.get('email') or '').strip()

        if not guest_phone:
            guest_phone = (primary_guest.get('phone') or '').strip()

        if not special_requests:
            special_request_parts = []
            if preferences.get('specialRequests'):
                special_request_parts.append(str(preferences.get('specialRequests')).strip())
            if preferences.get('arrivalTime'):
                special_request_parts.append(f"Arrival time: {str(preferences.get('arrivalTime')).strip()}")
            if preferences.get('bedPreference') and preferences.get('bedPreference') != 'no_preference':
                special_request_parts.append(f"Bed preference: {str(preferences.get('bedPreference')).strip()}")
            if preferences.get('smokingPreference') and preferences.get('smokingPreference') != 'no_preference':
                special_request_parts.append(f"Smoking preference: {str(preferences.get('smokingPreference')).strip()}")

            selected_enhancements = [
                key for key, enabled in enhancements.items()
                if enabled and key in ENHANCEMENT_PRICES
            ]
            if selected_enhancements:
                special_request_parts.append(
                    'Enhancements: ' + ', '.join(selected_enhancements)
                )

            special_requests = ' | '.join(special_request_parts)

        if not all([check_in, check_out, guest_name, guest_email, guest_phone]):
            return bad_request('Check-in, check-out, guest name, email, and phone are required.')

        adults = int(data.get('adults', 1))
        children = int(data.get('children', 0))
        room_id = int(data.get('roomId'))

        if adults < 1:
            return bad_request('At least one adult is required.')
        if children < 0:
            return bad_request('Children count cannot be negative.')
        if len(guest_name) < 2:
            return bad_request('Guest name must be at least 2 characters long.')
        if '@' not in guest_email or '.' not in guest_email.split('@')[-1]:
            return bad_request('Please enter a valid email address.')

        phone_digits = ''.join(ch for ch in guest_phone if ch.isdigit())
        if len(phone_digits) < 7:
            return bad_request('Please enter a valid phone number.')

        check_in_date = parse_date(check_in, 'check-in date')
        check_out_date = parse_date(check_out, 'check-out date')
        if check_out_date <= check_in_date:
            return bad_request('Check-out date must be after check-in date.')

        room = db.session.get(Room, room_id)
        if room is None:
            return bad_request('Selected room does not exist.')
        if adults + children > infer_room_capacity(room.bed):
            return bad_request('This room cannot accommodate the selected guests.')
        if has_overlapping_reservation(room_id, check_in_date, check_out_date):
            return bad_request('This room is not available for the selected dates.')

        nights = (check_out_date - check_in_date).days
        nightly_rate = parse_price(room.price)
        enhancement_total = get_enhancement_total(enhancements)
        total_price = format_price((nightly_rate * nights) + enhancement_total)

        reservation = Reservation(
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            room_id=room_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            special_requests=special_requests,
            total_price=total_price
        )
        db.session.add(reservation)
        db.session.commit()
        return {
            "success": True,
            "reservation_id": reservation.id,
            "total_price": total_price,
            "room_name": room.name
        }, 200
    except ValueError as exc:
        db.session.rollback()
        return bad_request(str(exc))
    except Exception:
        db.session.rollback()
        app.logger.exception('Reservation creation failed')
        return {"success": False, "error": 'Reservation could not be completed.'}, 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
