from src.booking_app import app

if __name__ == '__main__':
    # Start the decoupled reservation microservice
    app.run(debug=True, port=5001)
