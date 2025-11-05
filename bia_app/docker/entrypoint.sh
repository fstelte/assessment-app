#!/bin/bash
set -e

echo "Starting BIA Tool Docker Container..."

# Initialize database
echo "Initializing database..."
python -c "
from app import create_app, db
from app.models import User
import os

app = create_app()
with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if admin_email and admin_password:
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            try:
                from app.commands import create_admin_user
                create_admin_user()
                print(f'Admin user created: {admin_email}')
            except Exception as e:
                print(f'Could not create admin user: {e}')
        else:
            print(f'Admin user already exists: {admin_email}')
"

echo "Starting Flask application..."
exec python run.py