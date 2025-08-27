@echo off
echo ========================================
echo SUPERPARAGUAI SECURITY - STEP 1
echo ========================================
echo.
echo This script will install basic security packages
echo that won't break your Django server.
echo.

echo [1/3] Installing Basic Security Packages...
pip install django-ratelimit==4.1.0
if %errorlevel% neq 0 (
    echo WARNING: Failed to install django-ratelimit
    echo This is not critical for basic security
)

pip install bleach==6.1.0
if %errorlevel% neq 0 (
    echo WARNING: Failed to install bleach
    echo This is not critical for basic security
)

echo.
echo [2/3] Basic Security Packages Installed!
echo.
echo [3/3] Next Steps:
echo 1. Test your Django server: python manage.py runserver
echo 2. If it works, run: scripts/install_security_step2.bat
echo 3. If it fails, we'll fix it step by step
echo.
echo ========================================
echo BASIC SECURITY READY!
echo ========================================
echo.
pause
