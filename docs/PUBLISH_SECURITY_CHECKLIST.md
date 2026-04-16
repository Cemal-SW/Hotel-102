# Publish Security Checklist

## Secrets And Config
- Set `HOTEL102_ENV=production`.
- Set a strong `FLASK_SECRET_KEY`.
- Set `DATABASE_URL` for the production database if you are not using the default SQLite file.
- Set `BOOKING_URL=/booking/` and `MAIN_URL=/` when using the combined WSGI app.
- Set `BOOKING_PUBLIC_URL` to the public booking URL if callbacks need an explicit absolute URL.
- Set `IYZICO_MODE=live` only after live keys are ready.
- Set `IYZICO_API_KEY` and `IYZICO_SECRET_KEY` from the hosting secrets panel.

## Admin Security
- Create the first admin manually with `python scripts/create_admin.py --username <name>`.
- Do not reintroduce default admin credentials in seed or startup scripts.
- Enable HTTPS and set `SESSION_COOKIE_SECURE=true`.
- Optionally add `ADMIN_ALLOWED_IPS` and/or `ADMIN_BASIC_AUTH_USERNAME` + `ADMIN_BASIC_AUTH_PASSWORD`.
- Keep `/admin/login` rate limiting enabled.

## File Upload Safety
- Upload only local image or MP4 files through the admin.
- Do not allow SVG, HTML, or script-capable uploads.
- Verify that uploaded files are served only from `/uploads/<filename>` and only with allowed extensions.

## Booking And Payment
- Use the hosted iyzico payment flow only.
- Keep `/api/reserve` disabled in production.
- Verify that booking drafts persist across restarts in the database.
- Test the full callback flow with the final production callback URL.

## Hosting
- Prefer the combined `wsgi.py` / `passenger_wsgi.py` entrypoint for shared hosting.
- Prebuild booking CSS before deployment or set `BUILD_BOOKING_CSS_ON_REQUEST=true` only temporarily.
- Avoid running two separate Flask processes against the same SQLite file in production.

## Final Verification
- Confirm `debug` is off for both apps.
- Confirm `/admin` requires login and CSRF-protected POST actions still work.
- Confirm uploads, room reorder, gallery delete, experience delete, and settings update all succeed.
- Confirm booking works under `/booking/` and callback returns to step 5 correctly.
- Confirm security headers are present on public and admin pages.
