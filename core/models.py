from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hero_type = db.Column(db.String(50), default='image') # 'image' or 'video'
    hero_media = db.Column(db.String(500), nullable=True) # URL or filename

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    hero_img = db.Column(db.String(500), nullable=True) # URL or filename
    desc = db.Column(db.Text, nullable=True)
    short_desc = db.Column(db.String(300), nullable=True)
    sqm = db.Column(db.Integer, nullable=True)
    bed = db.Column(db.String(50), nullable=True)
    price = db.Column(db.String(50), nullable=True) # Could be String for "$1,250" or Integer
    base_adults = db.Column(db.Integer, nullable=True)
    base_children = db.Column(db.Integer, nullable=True)
    max_adults = db.Column(db.Integer, nullable=True)
    max_children = db.Column(db.Integer, nullable=True)
    max_occupancy = db.Column(db.Integer, nullable=True)
    allows_extra_bed = db.Column(db.Boolean, nullable=True, default=True)
    available = db.Column(db.Boolean, nullable=True, default=True)
    quantity_available = db.Column(db.Integer, nullable=True, default=1)
    order_index = db.Column(db.Integer, default=0)
    photos = db.relationship('RoomPhoto', backref='room', lazy=True, cascade="all, delete-orphan")

class RoomPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    photo_url = db.Column(db.String(500), nullable=False)
    position = db.Column(db.Integer, default=0) # Display order

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    order_index = db.Column(db.Integer, default=0)

class GalleryImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(300), nullable=True)
    col_span = db.Column(db.Integer, default=1)
    row_span = db.Column(db.Integer, default=1)
    order_index = db.Column(db.Integer, default=0)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_in = db.Column(db.String(50), nullable=False)
    check_out = db.Column(db.String(50), nullable=False)
    adults = db.Column(db.Integer, nullable=False)
    children = db.Column(db.Integer, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    room_count = db.Column(db.Integer, nullable=False, default=1)
    guest_name = db.Column(db.String(150), nullable=False)
    guest_email = db.Column(db.String(150), nullable=False)
    guest_phone = db.Column(db.String(50), nullable=False)
    special_requests = db.Column(db.Text, nullable=True)
    total_price = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default='Pending') # Pending, Confirmed, Cancelled
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class BookingDraft(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    public_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    checkout_token = db.Column(db.String(255), unique=True, nullable=True, index=True)
    payload_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


ROOM_BOOKING_COLUMN_SQL = {
    'base_adults': 'ALTER TABLE room ADD COLUMN base_adults INTEGER',
    'base_children': 'ALTER TABLE room ADD COLUMN base_children INTEGER',
    'max_adults': 'ALTER TABLE room ADD COLUMN max_adults INTEGER',
    'max_children': 'ALTER TABLE room ADD COLUMN max_children INTEGER',
    'max_occupancy': 'ALTER TABLE room ADD COLUMN max_occupancy INTEGER',
    'allows_extra_bed': 'ALTER TABLE room ADD COLUMN allows_extra_bed BOOLEAN',
    'available': 'ALTER TABLE room ADD COLUMN available BOOLEAN',
    'quantity_available': 'ALTER TABLE room ADD COLUMN quantity_available INTEGER',
}

RESERVATION_COLUMN_SQL = {
    'room_count': 'ALTER TABLE reservation ADD COLUMN room_count INTEGER DEFAULT 1',
}


def ensure_room_booking_columns():
    inspector = inspect(db.engine)
    if 'room' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('room')}
    missing_columns = [
        column_name
        for column_name in ROOM_BOOKING_COLUMN_SQL
        if column_name not in existing_columns
    ]

    if not missing_columns:
        return

    with db.engine.begin() as connection:
        for column_name in missing_columns:
            connection.execute(text(ROOM_BOOKING_COLUMN_SQL[column_name]))


def initialize_database():
    db.create_all()
    ensure_room_booking_columns()
    inspector = inspect(db.engine)
    if 'reservation' in inspector.get_table_names():
        reservation_columns = {column['name'] for column in inspector.get_columns('reservation')}
        missing_reservation_columns = [
            column_name
            for column_name in RESERVATION_COLUMN_SQL
            if column_name not in reservation_columns
        ]
        if missing_reservation_columns:
            with db.engine.begin() as connection:
                for column_name in missing_reservation_columns:
                    connection.execute(text(RESERVATION_COLUMN_SQL[column_name]))
