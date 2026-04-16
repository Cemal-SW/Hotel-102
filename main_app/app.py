import os
from flask import Flask, abort, jsonify, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
from core.config import BaseConfig
from core.security import (
    apply_security_headers,
    check_login_rate_limit,
    clear_login_rate_limit,
    enforce_admin_access_controls,
    enforce_https_redirect,
    register_failed_login_attempt,
    register_security_context,
    should_validate_csrf,
    validate_csrf,
)
from core.uploads import UploadValidationError, is_public_upload, save_uploaded_file

app.config.from_object(BaseConfig)

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # Hotel-102 root

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

from core.models import db, User, Room, RoomPhoto, Experience, GalleryImage, Settings, Reservation, initialize_database

db.init_app(app)
app.jinja_env.auto_reload = True
login_manager = LoginManager(app)
login_manager.session_protection = 'strong'

login_manager.login_view = 'admin_login'
register_security_context(app)


@app.before_request
def apply_pre_request_security():
    https_redirect = enforce_https_redirect()
    if https_redirect is not None:
        return https_redirect
    enforce_admin_access_controls()
    if should_validate_csrf():
        validate_csrf()


@app.after_request
def add_security_headers(response):
    return apply_security_headers(response)

with app.app_context():
    initialize_database()

BOOKING_URL = app.config['BOOKING_URL']


def parse_optional_int_field(value):
    value = str(value or '').strip()
    if not value:
        return None
    return max(0, int(value))


def parse_checkbox_field(name):
    return request.form.get(name) == 'on'


def populate_room_from_form(room):
    room.name = (request.form.get('name') or '').strip()
    room.slug = (request.form.get('slug') or '').strip()
    room.price = (request.form.get('price') or '').strip()
    room.sqm = parse_optional_int_field(request.form.get('sqm'))
    room.bed = (request.form.get('bed') or '').strip()
    room.short_desc = (request.form.get('short_desc') or '').strip()
    room.desc = (request.form.get('desc') or '').strip()
    room.base_adults = parse_optional_int_field(request.form.get('base_adults'))
    room.base_children = parse_optional_int_field(request.form.get('base_children'))
    room.max_adults = parse_optional_int_field(request.form.get('max_adults'))
    room.max_children = parse_optional_int_field(request.form.get('max_children'))
    room.max_occupancy = parse_optional_int_field(request.form.get('max_occupancy'))
    room.quantity_available = parse_optional_int_field(request.form.get('quantity_available'))
    room.allows_extra_bed = parse_checkbox_field('allows_extra_bed')
    room.available = parse_checkbox_field('available')


def validate_room_form(room, current_room_id=None):
    if not room.name:
        return 'Room name is required.'
    if not room.slug:
        return 'Room slug is required.'
    if not room.price:
        return 'Room price is required.'

    existing_room = Room.query.filter_by(slug=room.slug).first()
    if existing_room and existing_room.id != current_room_id:
        return 'That room slug is already in use.'

    return None


def save_room_cover_image(room):
    if 'hero_img' not in request.files or request.files['hero_img'].filename == '':
        return

    file = request.files['hero_img']
    filename = save_uploaded_file(
        file,
        app.config['UPLOAD_FOLDER'],
        allowed_extensions=set(app.config['ALLOWED_IMAGE_EXTENSIONS']),
        allowed_mime_prefixes=tuple(app.config['ALLOWED_IMAGE_MIME_PREFIXES']),
    )
    room.hero_img = filename


def save_uploaded_media(file, *, kind):
    if kind == 'image':
        return save_uploaded_file(
            file,
            app.config['UPLOAD_FOLDER'],
            allowed_extensions=set(app.config['ALLOWED_IMAGE_EXTENSIONS']),
            allowed_mime_prefixes=tuple(app.config['ALLOWED_IMAGE_MIME_PREFIXES']),
        )
    if kind == 'hero_media':
        image_extensions = set(app.config['ALLOWED_IMAGE_EXTENSIONS'])
        video_extensions = set(app.config['ALLOWED_VIDEO_EXTENSIONS'])
        extension = os.path.splitext(secure_filename(file.filename or ''))[1].lower()
        if extension in video_extensions:
            return save_uploaded_file(
                file,
                app.config['UPLOAD_FOLDER'],
                allowed_extensions=video_extensions,
                allowed_mime_types=set(app.config['ALLOWED_VIDEO_MIME_TYPES']),
            )
        return save_uploaded_file(
            file,
            app.config['UPLOAD_FOLDER'],
            allowed_extensions=image_extensions,
            allowed_mime_prefixes=tuple(app.config['ALLOWED_IMAGE_MIME_PREFIXES']),
        )
    raise UploadValidationError('Unsupported upload category.')


def normalize_room_order():
    rooms = Room.query.order_by(Room.order_index, Room.id).all()
    for index, room in enumerate(rooms):
        room.order_index = index

@app.context_processor
def inject_globals():
    return dict(BOOKING_URL=BOOKING_URL)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ====== PUBLIC ROUTES ======

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not is_public_upload(filename, allowed_extensions=set(app.config['PUBLIC_UPLOAD_EXTENSIONS'])):
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    settings = Settings.query.first()
    rooms = Room.query.order_by(Room.order_index).limit(3).all()
    experiences = Experience.query.order_by(Experience.order_index).limit(3).all()
    gallery = GalleryImage.query.order_by(GalleryImage.order_index).limit(5).all()
    return render_template('index.html', settings=settings, rooms=rooms, experiences=experiences, gallery=gallery)

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/rooms.html')
def rooms():
    all_rooms = Room.query.order_by(Room.order_index).all()
    return render_template('rooms.html', rooms=all_rooms)

@app.route('/<slug>.html')
def room_detail(slug):
    room = Room.query.filter_by(slug=slug).first()
    if room:
        return render_template('room.html', room=room)
    abort(404)

@app.route('/experiences.html')
def experiences():
    all_experiences = Experience.query.order_by(Experience.order_index).all()
    return render_template('experiences.html', experiences=all_experiences)

@app.route('/gallery.html')
def gallery():
    all_gallery = GalleryImage.query.order_by(GalleryImage.order_index).all()
    return render_template('gallery.html', gallery=all_gallery)

@app.route('/contact.html')
def contact():
    return render_template('contact.html')

# ====== ADMIN ROUTES (To be implemented) ======

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        retry_after = check_login_rate_limit(username)
        if retry_after is not None:
            flash(f'Too many login attempts. Try again in {retry_after} seconds.')
            return render_template('admin/login.html'), 429
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            clear_login_rate_limit(username)
            session.clear()
            login_user(user)
            session.permanent = True
            if app.config.get('LOG_ADMIN_EVENTS'):
                app.logger.info('Admin login succeeded for %s from %s', username, request.remote_addr)
            return redirect(url_for('admin_dashboard'))
        register_failed_login_attempt(username)
        if app.config.get('LOG_ADMIN_EVENTS'):
            app.logger.warning('Admin login failed for %s from %s', username or '<blank>', request.remote_addr)
        flash('Invalid username or password')
    return render_template('admin/login.html')

@app.route('/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    if app.config.get('LOG_ADMIN_EVENTS'):
        app.logger.info('Admin logout for %s from %s', getattr(request, 'remote_addr', 'unknown'), request.remote_addr)
    logout_user()
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    total_rooms = Room.query.count()
    total_exps = Experience.query.count()
    total_gallery = GalleryImage.query.count()
    return render_template('admin/dashboard.html', total_rooms=total_rooms, total_exps=total_exps, total_gallery=total_gallery)

@app.route('/admin/rooms')
@login_required
def admin_rooms():
    rooms = Room.query.order_by(Room.order_index).all()
    return render_template('admin/rooms.html', rooms=rooms)


@app.route('/admin/rooms/reorder', methods=['POST'])
@login_required
def admin_room_reorder():
    data = request.get_json(silent=True) or {}
    ordered_ids = data.get('ordered_ids')
    if not isinstance(ordered_ids, list) or not ordered_ids:
        return jsonify({'success': False, 'error': 'A non-empty room order is required.'}), 400

    parsed_ids = []
    for room_id in ordered_ids:
        try:
            parsed_ids.append(int(room_id))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Room order contains an invalid room id.'}), 400

    rooms = Room.query.order_by(Room.order_index, Room.id).all()
    existing_ids = [room.id for room in rooms]
    if sorted(parsed_ids) != sorted(existing_ids):
        return jsonify({'success': False, 'error': 'Room order must include every room exactly once.'}), 400

    room_map = {room.id: room for room in rooms}
    for index, room_id in enumerate(parsed_ids):
        room_map[room_id].order_index = index

    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/rooms/new', methods=['GET', 'POST'])
@login_required
def admin_room_create():
    room = Room(
        hero_img='',
        allows_extra_bed=True,
        available=True,
        quantity_available=1,
    )

    if request.method == 'POST':
        try:
            populate_room_from_form(room)
            validation_error = validate_room_form(room)
            if validation_error:
                flash(validation_error, 'error')
                return render_template('admin/room_edit.html', room=room, is_create=True)

            room.order_index = (db.session.query(db.func.max(Room.order_index)).scalar() or 0) + 1
            save_room_cover_image(room)
            db.session.add(room)
            db.session.commit()
            flash('Room created successfully! You can now add gallery photos.', 'success')
            return redirect(url_for('admin_room_edit', room_id=room.id))
        except UploadValidationError as exc:
            flash(str(exc), 'error')

    return render_template('admin/room_edit.html', room=room, is_create=True)

@app.route('/admin/rooms/<int:room_id>', methods=['GET', 'POST'])
@login_required
def admin_room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            populate_room_from_form(room)
            validation_error = validate_room_form(room, current_room_id=room.id)
            if validation_error:
                flash(validation_error, 'error')
                return render_template('admin/room_edit.html', room=room, is_create=False)

            save_room_cover_image(room)

            if 'detail_photo' in request.files and request.files['detail_photo'].filename != '':
                file = request.files['detail_photo']
                filename = save_uploaded_media(file, kind='image')
                position = int(request.form.get('photo_position', 4))
                new_photo = RoomPhoto(room_id=room.id, photo_url=filename, position=position)
                db.session.add(new_photo)

            db.session.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('admin_room_edit', room_id=room.id))
        except UploadValidationError as exc:
            flash(str(exc), 'error')

    return render_template('admin/room_edit.html', room=room, is_create=False)


@app.route('/admin/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
def admin_room_delete(room_id):
    room = Room.query.get_or_404(room_id)
    reservation_count = Reservation.query.filter_by(room_id=room.id).count()
    if reservation_count:
        flash('This room cannot be deleted because reservations already reference it.', 'error')
        return redirect(url_for('admin_rooms'))

    db.session.delete(room)
    db.session.commit()
    normalize_room_order()
    db.session.commit()
    flash('Room deleted successfully.', 'success')
    return redirect(url_for('admin_rooms'))

@app.route('/admin/rooms/<int:room_id>/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
def admin_room_photo_delete(room_id, photo_id):
    photo = RoomPhoto.query.filter_by(id=photo_id, room_id=room_id).first_or_404()
    db.session.delete(photo)
    db.session.commit()
    flash('Detail photo removed.', 'success')
    return redirect(url_for('admin_room_edit', room_id=room_id))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings(hero_type='image', hero_media='')
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            hero_type = request.form.get('hero_type')
            if hero_type in ['image', 'video']:
                settings.hero_type = hero_type
                
            if 'hero_media' in request.files and request.files['hero_media'].filename != '':
                file = request.files['hero_media']
                filename = save_uploaded_media(file, kind='hero_media')
                settings.hero_media = filename
                
            db.session.commit()
            flash('Settings updated.', 'success')
            return redirect(url_for('admin_settings'))
        except UploadValidationError as exc:
            flash(str(exc), 'error')
        
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/experiences', methods=['GET', 'POST'])
@login_required
def admin_experiences():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        try:
            if 'image' in request.files and request.files['image'].filename != '':
                file = request.files['image']
                filename = save_uploaded_media(file, kind='image')
                
                new_exp = Experience(title=title, description=description, image_url=filename)
                db.session.add(new_exp)
                db.session.commit()
                flash('Experience added successfully.', 'success')
            else:
                flash('An image is required.', 'error')
        except UploadValidationError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('admin_experiences'))
        
    experiences = Experience.query.all()
    return render_template('admin/experiences.html', experiences=experiences)

@app.route('/admin/experiences/<int:exp_id>/delete', methods=['POST'])
@login_required
def admin_experiences_delete(exp_id):
    exp = Experience.query.get_or_404(exp_id)
    db.session.delete(exp)
    db.session.commit()
    flash('Experience removed.', 'success')
    return redirect(url_for('admin_experiences'))

@app.route('/admin/gallery', methods=['GET', 'POST'])
@login_required
def admin_gallery():
    if request.method == 'POST':
        try:
            if 'image' in request.files and request.files['image'].filename != '':
                file = request.files['image']
                filename = save_uploaded_media(file, kind='image')
                
                new_img = GalleryImage(image_url=filename)
                db.session.add(new_img)
                db.session.commit()
                flash('Gallery image added.', 'success')
            else:
                flash('An image is required.', 'error')
        except UploadValidationError as exc:
            flash(str(exc), 'error')
        return redirect(url_for('admin_gallery'))
        
    gallery = GalleryImage.query.all()
    return render_template('admin/gallery.html', gallery=gallery)

@app.route('/admin/gallery/<int:img_id>/delete', methods=['POST'])
@login_required
def admin_gallery_delete(img_id):
    img = GalleryImage.query.get_or_404(img_id)
    db.session.delete(img)
    db.session.commit()
    flash('Gallery image removed.', 'success')
    return redirect(url_for('admin_gallery'))

# Start the application
if __name__ == '__main__':
    app.run(debug=app.debug, port=5000)
