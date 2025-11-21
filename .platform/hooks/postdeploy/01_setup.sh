#!/bin/bash
source /var/app/venv/*/bin/activate
cd /var/app/current

echo "=== COMPLETE DATABASE SETUP ==="

echo "1. Checking current directory..."
pwd
ls -la

echo "2. Running migrations..."
python manage.py migrate

echo "3. Checking database file..."
if [ -f "db.sqlite3" ]; then
    echo "Database file exists, setting permissions..."
    chmod 664 db.sqlite3
else
    echo "Database file not found in current directory"
fi

echo "4. Checking menu items..."
python manage.py shell -c "
from menu.models import MenuItem
count = MenuItem.objects.count()
print(f'Current menu items: {count}')
if count < 12:
    print('Loading initial data...')
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'loaddata', 'initial_data.json'])
    print('Data loaded successfully')
else:
    print('Already have 12+ items')
"

echo "5. Ensuring admin user..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'hetikchandaria67@gmail.com', 'admin123')
    print('Admin user created')
else:
    print('Admin user exists')
"

echo "6. Final verification..."
python manage.py shell -c "
from menu.models import MenuItem
import os
print(f'Final menu items: {MenuItem.objects.count()}')
print(f'Database file exists: {os.path.exists(\"db.sqlite3\")}')
"

echo "=== SETUP COMPLETE ==="