from __future__ import annotations

import os

from werkzeug.middleware.dispatcher import DispatcherMiddleware


os.environ.setdefault('BOOKING_URL', '/booking/')
os.environ.setdefault('MAIN_URL', '/')

from main_app.app import app as main_app  # noqa: E402
from booking_app.app import app as booking_app  # noqa: E402


application = DispatcherMiddleware(main_app, {
    '/booking': booking_app,
})

