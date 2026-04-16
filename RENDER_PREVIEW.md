# Render Preview Deployment

This project is configured to run on Render as a single preview service:

- `/` serves the promotional website and admin panel
- `/booking/` serves the reservation flow

## Included files

- `render.yaml` provisions one web service and one Postgres database
- `wsgi.py` is the combined WSGI entrypoint used by Gunicorn

## Before first deploy

Set these Render environment variables if you do not want to use the defaults in `render.yaml`:

- `BOOKING_PUBLIC_URL=https://<your-service>.onrender.com/booking`
- `IYZICO_API_KEY`
- `IYZICO_SECRET_KEY`

`FLASK_SECRET_KEY`, `HOTEL102_ENV`, `BOOKING_URL`, `MAIN_URL`, `TRUST_PROXY_HEADERS`, `SESSION_COOKIE_SECURE`, and `FLASK_DEBUG` are already defined in the blueprint.

## Create the first admin user

After the first successful deploy, open the Render shell for the web service and run:

```bash
python scripts/create_admin.py --username <admin-username>
```

You will be prompted for a password.

## Preview notes

- The deploy is optimized for demo/staging use, not final production hardening.
- Booking drafts and app data should live in the provisioned Postgres database.
- File uploads still use local disk storage, so uploaded files are not ideal for long-term persistence across rebuilds.
