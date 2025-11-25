#!/bin/bash
source /var/app/venv/*/bin/activate
cd /var/app/current

# Defined in your settings.py
DB_FOLDER="/var/app/data"
DB_PATH="$DB_FOLDER/db.sqlite3"

echo "=== EB DEPLOY: DATABASE SETUP ==="

# 1. Create the persistent data directory if it doesn't exist
if [ ! -d "$DB_FOLDER" ]; then
    echo "Creating data directory..."
    mkdir -p "$DB_FOLDER"
    # IMPORTANT: Give webapp user ownership of the folder so it can write temp files
    chown webapp:webapp "$DB_FOLDER"
    chmod 775 "$DB_FOLDER"
fi

# 2. Ensure persistent SQLite exists
if [ ! -f "$DB_PATH" ]; then
    echo "Creating new persistent DB at $DB_PATH"
    # Copy the empty DB template from the deployment
    if [ -f "db.sqlite3" ]; then
        cp db.sqlite3 "$DB_PATH"
    else
        # If no local DB was uploaded, Django will create one on migrate, 
        # but we touch it here to set permissions correctly.
        touch "$DB_PATH"
    fi
else
    echo "Using existing persistent DB at $DB_PATH"
fi

# 3. CRITICAL: Fix Permissions so 'webapp' user can write to it
chown webapp:webapp "$DB_PATH"
chmod 664 "$DB_PATH"

# 4. Migrations (Now pointing to the persistent DB via settings.py)
python manage.py migrate --noinput

# 5. Load initial data
python manage.py shell -c "
from menu.models import MenuItem
from django.core.management import call_command
try:
    if MenuItem.objects.count() < 12:
        call_command('loaddata', 'initial_data.json')
        print('Initial data loaded.')
    else:
        print('Initial data already exists.')
except Exception as e:
    print(f'Skipping data load: {e}')
"

# 6. Create admin user
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'hetikchandaria67@gmail.com', 'admin123')
    print('Admin created')
else:
    print('Admin exists')
"

echo "=== EB DEPLOY COMPLETE ==="