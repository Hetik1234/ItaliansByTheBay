#!/bin/bash
echo "== PREDEPLOY: Adjusting permissions =="

# Ensure scripts are executable
chmod +x /var/app/staging/.platform/hooks/postdeploy/01_setup.sh || true

# Ensure app directory is readable
chmod -R 755 /var/app/staging || true

echo "== PREDEPLOY COMPLETE =="
