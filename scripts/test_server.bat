@echo off
echo ========================================
echo TESTING DJANGO SERVER
echo ========================================
echo.
echo Testing if Django server can start...
echo.

echo [1/2] Testing server startup...
python manage.py check --deploy
if %errorlevel% neq 0 (
    echo.
    echo ❌ SERVER CONFIGURATION HAS ERRORS
    echo Check the errors above and fix them
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Configuration check passed!
echo.
echo ✅ Your Django server should work now!
echo.
echo Try starting it with: python manage.py runserver
echo.
echo ========================================
echo SERVER READY TO START!
echo ========================================
echo.
pause
