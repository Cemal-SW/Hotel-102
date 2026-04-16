from __future__ import annotations

import argparse
import getpass
import os
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_app.app import app  # noqa: E402
from core.models import User, db  # noqa: E402


def build_parser():
    parser = argparse.ArgumentParser(description='Create a Hotel-102 admin user.')
    parser.add_argument('--username', required=True, help='Admin username')
    parser.add_argument('--password', help='Admin password (omit to prompt securely)')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    password = args.password or getpass.getpass('Admin password: ')
    if len(password) < 12:
        raise SystemExit('Password must be at least 12 characters long.')

    with app.app_context():
        existing_user = User.query.filter_by(username=args.username.strip()).first()
        if existing_user:
            raise SystemExit(f'User "{args.username}" already exists.')

        admin = User(username=args.username.strip())
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

    print(f'Admin user "{args.username}" created successfully.')


if __name__ == '__main__':
    main()
