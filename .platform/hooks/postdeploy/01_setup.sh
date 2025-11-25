#!/bin/bash
source /var/app/venv/*/bin/activate
cd /var/app/current

DB_PATH="/var/app/data/db.sqlite3"

echo "=== EB DEPLOY: DATABASE SETUP ==="

# 1. Migrations
python manage.py migrate --noinput

# 2. Ensure persistent SQLite exists
if [ ! -f "$DB_PATH" ]; then
    echo "Creating new persistent DB at $DB_PATH"
    cp db.sqlite3 "$DB_PATH"
else
    echo "Using existing persistent DB at $DB_PATH"
fi

chmod 664 "$DB_PATH"

# 3. Load initial data
python manage.py shell -c "
from menu.models import MenuItem
from django.core.management import call_command
if MenuItem.objects.count() < 12:
    call_command('loaddata', 'initial_data.json')
    print('Initial data loaded.')
else:
    print('Initial data already exists.')
"

# 4. Create admin user
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
