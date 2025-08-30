#!/usr/bin/env python
"""
Railway Startup Script
Handles database setup, migrations, and static files collection
"""
import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection

def setup_database():
    """Ensure database is properly set up"""
    try:
        # Run migrations
        print("🔄 Running database migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations completed successfully")
        
        # Check if superuser exists, create if not
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(is_superuser=True).exists():
            print("👤 Creating superuser...")
            from django.core.management import call_command
            call_command('createsuperuser', 
                        username='admin',
                        email='admin@example.com',
                        interactive=False)
            print("✅ Superuser created successfully")
        else:
            print("✅ Superuser already exists")
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)

def collect_static():
    """Collect static files"""
    try:
        print("📁 Collecting static files...")
        print(f"📂 Static root: {os.environ.get('STATIC_ROOT', 'Not set')}")
        print(f"📂 Static URL: {os.environ.get('STATIC_URL', 'Not set')}")
        
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        print("✅ Static files collected successfully")
        
        # Verify static files were collected
        static_root = os.environ.get('STATIC_ROOT', 'staticfiles')
        if os.path.exists(static_root):
            print(f"📁 Static files directory exists: {static_root}")
            print(f"📁 Files in static directory: {len(os.listdir(static_root))}")
        else:
            print(f"❌ Static files directory not found: {static_root}")
            
    except Exception as e:
        print(f"❌ Static file collection failed: {e}")
        sys.exit(1)

def verify_settings():
    """Verify Django settings are correct"""
    try:
        print("🔍 Verifying Django settings...")
        
        # Check if Jazzmin is in INSTALLED_APPS
        from django.conf import settings
        if 'jazzmin' in settings.INSTALLED_APPS:
            print("✅ Jazzmin is in INSTALLED_APPS")
        else:
            print("❌ Jazzmin is NOT in INSTALLED_APPS")
            
        # Check static files configuration
        print(f"📁 STATIC_URL: {settings.STATIC_URL}")
        print(f"📁 STATIC_ROOT: {settings.STATIC_ROOT}")
        print(f"📁 STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
        
        # Check middleware
        if 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE:
            print("✅ WhiteNoise middleware is configured")
        else:
            print("❌ WhiteNoise middleware is NOT configured")
            
    except Exception as e:
        print(f"❌ Settings verification failed: {e}")

def main():
    """Main startup function"""
    print("🚀 Starting Railway deployment...")
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()
    
    # Verify settings
    verify_settings()
    
    # Setup database
    setup_database()
    
    # Collect static files
    collect_static()
    
    print("🎉 Startup script completed successfully!")
    print("🚀 Starting Gunicorn server...")

if __name__ == '__main__':
    main()
