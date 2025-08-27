@echo off
echo ========================================
echo TESTING DJANGO SERVER - SIMPLE CHECK
echo ========================================
echo.
echo Testing basic Django configuration...
echo.

echo [1/2] Testing Django settings...
python manage.py check --deploy
if %errorlevel% neq 0 (
    echo.
    echo ❌ DJANGO CONFIGURATION HAS ERRORS
    echo.
    echo Let's try a simpler approach...
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Django configuration looks good!
echo.
echo ✅ Try starting the server now:
echo python manage.py runserver
echo.
echo ========================================
echo READY TO TEST SERVER!
echo ========================================
echo.
pause
