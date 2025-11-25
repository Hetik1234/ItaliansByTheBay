#!/bin/bash
source /var/app/venv/*/bin/activate
cd /var/app/current

DB_PATH="/var/app/data/db.sqlite3"

echo "=== EB POSTDEPLOY START ==="

# 1. Migrate
python manage.py migrate --noinput

# 2. Create persistent database
if [ ! -f "$DB_PATH" ]; then
    echo "Creating persistent DB"
    cp db.sqlite3 "$DB_PATH"
else
    echo "Reusing existing persistent DB"
fi

chmod 664 "$DB_PATH"

# 3. Load initial data
python manage.py shell - << 'EOF'
from menu.models import MenuItem
from django.core.management import call_command

if MenuItem.objects.count() < 12:
    call_command("loaddata", "initial_data.json")
    print("Initial data loaded")
else:
    print("Initial data already present")
EOF

# 4. Admin account
python manage.py shell - << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin123")
    print("Admin user created")
else:
    print("Admin user exists")
EOF

echo "=== EB POSTDEPLOY COMPLETE ==="
