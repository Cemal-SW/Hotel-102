import os
from flask import Flask, render_template, request, send_from_directory
from src.models import db, Room, Reservation

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # Root dir
db_path = os.path.join(basedir, 'data', 'instance', 'hotel.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

MAIN_URL = os.environ.get('MAIN_URL', 'http://127.0.0.1:5000/')

@app.context_processor
def inject_globals():
    return dict(MAIN_URL=MAIN_URL)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(basedir, 'data', 'uploads')
    return send_from_directory(upload_folder, filename)

@app.route('/')
def booking():
    rooms = Room.query.order_by(Room.order_index).all()
    return render_template('booking.html', rooms=rooms)

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    try:
        data = request.json
        reservation = Reservation(
            check_in=data.get('checkIn'),
            check_out=data.get('checkOut'),
            adults=int(data.get('adults', 1)),
            children=int(data.get('children', 0)),
            room_id=int(data.get('roomId')),
            guest_name=data.get('guestName'),
            guest_email=data.get('guestEmail'),
            guest_phone=data.get('guestPhone'),
            special_requests=data.get('specialRequests', ''),
            total_price=data.get('totalPrice', '0')
        )
        db.session.add(reservation)
        db.session.commit()
        return {"success": True, "reservation_id": reservation.id}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)
