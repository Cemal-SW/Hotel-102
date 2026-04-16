from booking_app.app import app

if __name__ == '__main__':
    # Start the decoupled reservation microservice
    app.run(debug=app.debug, port=5001)
