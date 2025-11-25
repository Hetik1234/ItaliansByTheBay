#!/bin/bash
source /var/app/venv/*/bin/activate

# --- PREDEPLOY FIX ---
# We use 'staging' because in the predeploy phase, the new code 
# hasn't been moved to 'current' yet.
cd /var/app/staging

# Defined in your settings.py
DB_FOLDER="/var/app/data"
DB_PATH="$DB_FOLDER/db.sqlite3"

echo "=== EB PRE-DEPLOY: DATABASE SETUP ==="

# 1. Create the persistent data directory (idempotent)
mkdir -p "$DB_FOLDER"

# 2. CRITICAL FIX: Always force folder ownership to 'webapp'
# SQLite needs to write a journal file into this directory.
# If this folder is owned by root, the DB is read-only.
chown -R webapp:webapp "$DB_FOLDER"
chmod 775 "$DB_FOLDER"

# 3. Handle the Database File
if [ ! -f "$DB_PATH" ]; then
    echo "Creating new persistent DB at $DB_PATH"
    if [ -f "db.sqlite3" ]; then
        cp db.sqlite3 "$DB_PATH"
    else
        touch "$DB_PATH"
    fi
else
    echo "Using existing persistent DB at $DB_PATH"
fi

# 4. CRITICAL FIX: Ensure the DB file itself is owned by webapp
chown webapp:webapp "$DB_PATH"
chmod 664 "$DB_PATH"

# 5. Migrations
python manage.py migrate --noinput

# 6. Load initial data
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

# 7. Create admin user
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'hetikchandaria67@gmail.com', 'admin123')
    print('Admin created')
else:
    print('Admin exists')
"

echo "=== EB PRE-DEPLOY COMPLETE ==="