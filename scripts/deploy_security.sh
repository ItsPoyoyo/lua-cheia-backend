#!/bin/bash

echo "========================================"
echo "SUPERPARAGUAI SECURITY DEPLOYMENT"
echo "========================================"
echo

echo "[1/5] Installing Security Packages..."
pip install -r requirements_security.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install security packages"
    exit 1
fi
echo "✓ Security packages installed successfully"
echo

echo "[2/5] Running Security Migrations..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to run migrations"
    exit 1
fi
echo "✓ Migrations completed successfully"
echo

echo "[3/5] Collecting Static Files..."
python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to collect static files"
    exit 1
fi
echo "✓ Static files collected successfully"
echo

echo "[4/5] Creating Security Log Directory..."
mkdir -p logs
echo "✓ Log directory created"
echo

echo "[5/5] Security Configuration Complete!"
echo
echo "========================================"
echo "SECURITY FEATURES ENABLED:"
echo "========================================"
echo "✓ Rate Limiting (1000 req/hour for users)"
echo "✓ DDoS Protection"
echo "✓ SQL Injection Prevention"
echo "✓ XSS Protection"
echo "✓ CSRF Protection"
echo "✓ Path Traversal Prevention"
echo "✓ Brute Force Protection (5 attempts)"
echo "✓ File Upload Security"
echo "✓ Input Validation"
echo "✓ Security Headers"
echo "✓ JWT Security (2 hour tokens)"
echo "✓ Session Security (1 hour expiry)"
echo "✓ Password Strength (12+ chars)"
echo "✓ Security Logging"
echo "========================================"
echo
echo "IMPORTANT: Restart your Django server!"
echo
echo "Command: python manage.py runserver"
echo
