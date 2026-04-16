from main_app.app import app

if __name__ == '__main__':
    # Start the primary marketing and admin application
    app.run(debug=app.debug, port=5000)
