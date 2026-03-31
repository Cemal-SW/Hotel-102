import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # 50MB for video uploads

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# Models
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ====== PUBLIC ROUTES ======

@app.route('/uploads/<filename>')
def uploaded_file(filename):
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
    # Forward common statics or missed htmls
    return render_template(f'{slug}.html')

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
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
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

@app.route('/admin/rooms/<int:room_id>', methods=['GET', 'POST'])
@login_required
def admin_room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.name = request.form.get('name')
        room.slug = request.form.get('slug')
        room.price = request.form.get('price')
        room.sqm = request.form.get('sqm')
        room.bed = request.form.get('bed')
        room.short_desc = request.form.get('short_desc')
        room.desc = request.form.get('desc')
        
        # Room Cover Image
        if 'hero_img' in request.files and request.files['hero_img'].filename != '':
            file = request.files['hero_img']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            room.hero_img = filename

        # Detail Photos
        if 'detail_photo' in request.files and request.files['detail_photo'].filename != '':
            file = request.files['detail_photo']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            position = int(request.form.get('photo_position', 4))
            new_photo = RoomPhoto(room_id=room.id, photo_url=filename, position=position)
            db.session.add(new_photo)

        db.session.commit()
        flash('Room updated successfully!', 'success')
        return redirect(url_for('admin_room_edit', room_id=room.id))

    return render_template('admin/room_edit.html', room=room)

@app.route('/admin/rooms/<int:room_id>/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
def admin_room_photo_delete(room_id, photo_id):
    photo = RoomPhoto.query.get_or_404(photo_id)
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
        hero_type = request.form.get('hero_type')
        if hero_type in ['image', 'video']:
            settings.hero_type = hero_type
            
        if 'hero_media' in request.files and request.files['hero_media'].filename != '':
            file = request.files['hero_media']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            settings.hero_media = filename
            
        db.session.commit()
        flash('Settings updated.', 'success')
        return redirect(url_for('admin_settings'))
        
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/experiences', methods=['GET', 'POST'])
@login_required
def admin_experiences():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_exp = Experience(title=title, description=description, image_url=filename)
            db.session.add(new_exp)
            db.session.commit()
            flash('Experience added successfully.', 'success')
            
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
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_img = GalleryImage(image_url=filename)
            db.session.add(new_img)
            db.session.commit()
            flash('Gallery image added.', 'success')
            
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
    with app.app_context():
        db.create_all()
        # Create default admin user if none exists
        if not User.query.first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Create default settings if none exists
            if not Settings.query.first():
                settings = Settings(hero_type='image', hero_media='https://lh3.googleusercontent.com/...')
                db.session.add(settings)
            
            db.session.commit()
    app.run(debug=True, port=5000)
