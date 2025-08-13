#!/usr/bin/env python3
"""
Security Audit Script for SuperParaguai E-commerce
Comprehensive security checks for production readiness
"""

import os
import sys
import django
import secrets
import hashlib
import re
from pathlib import Path
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import connection
from django.contrib.auth.models import User
from django.core.cache import cache

class SecurityAuditor:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
        self.score = 0
        self.total_checks = 0
        
    def log_issue(self, category, message, severity='HIGH'):
        """Log a security issue"""
        self.issues.append({
            'category': category,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now()
        })
        print(f"❌ {severity}: {category} - {message}")
        
    def log_warning(self, category, message):
        """Log a security warning"""
        self.warnings.append({
            'category': category,
            'message': message,
            'timestamp': datetime.now()
        })
        print(f"⚠️  WARNING: {category} - {message}")
        
    def log_pass(self, category, message):
        """Log a passed security check"""
        self.passed.append({
            'category': category,
            'message': message,
            'timestamp': datetime.now()
        })
        print(f"✅ PASS: {category} - {message}")
        self.score += 1
        self.total_checks += 1
        
    def check_environment_variables(self):
        """Check environment variables security"""
        print("\n🔐 Checking Environment Variables...")
        
        required_vars = [
            'DJANGO_SECRET_KEY',
            'DEBUG',
            'ALLOWED_HOSTS',
            'DATABASE_URL',
            'STRIPE_SECRET_KEY',
            'STRIPE_PUBLISHABLE_KEY',
            'STRIPE_WEBHOOK_SECRET',
        ]
        
        for var in required_vars:
            if not os.environ.get(var):
                self.log_issue('ENV_VARS', f'Missing required environment variable: {var}')
            else:
                self.log_pass('ENV_VARS', f'Environment variable {var} is set')
                
        # Check DEBUG setting
        if getattr(settings, 'DEBUG', True):
            self.log_issue('DEBUG', 'DEBUG is enabled in production', 'CRITICAL')
        else:
            self.log_pass('DEBUG', 'DEBUG is disabled')
            
        # Check SECRET_KEY strength
        secret_key = getattr(settings, 'SECRET_KEY', '')
        if len(secret_key) < 50:
            self.log_issue('SECRET_KEY', 'SECRET_KEY is too short (should be at least 50 characters)')
        else:
            self.log_pass('SECRET_KEY', 'SECRET_KEY meets length requirements')
            
    def check_database_security(self):
        """Check database security settings"""
        print("\n🗄️  Checking Database Security...")
        
        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.log_pass('DATABASE', 'Database connection successful')
        except Exception as e:
            self.log_issue('DATABASE', f'Database connection failed: {str(e)}')
            
        # Check database user permissions
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW GRANTS")
                grants = cursor.fetchall()
                for grant in grants:
                    if 'ALL PRIVILEGES' in str(grant) and 'ON *.*' in str(grant):
                        self.log_warning('DATABASE', 'Database user has excessive privileges')
                        break
                else:
                    self.log_pass('DATABASE', 'Database user has appropriate privileges')
        except Exception:
            self.log_warning('DATABASE', 'Could not check database privileges')
            
    def check_ssl_https_settings(self):
        """Check SSL/HTTPS configuration"""
        print("\n🔒 Checking SSL/HTTPS Configuration...")
        
        ssl_settings = [
            ('SECURE_SSL_REDIRECT', 'SSL redirect enabled'),
            ('SECURE_PROXY_SSL_HEADER', 'Proxy SSL header configured'),
            ('SECURE_HSTS_SECONDS', 'HSTS enabled'),
            ('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'HSTS includes subdomains'),
            ('SECURE_HSTS_PRELOAD', 'HSTS preload enabled'),
            ('SECURE_CONTENT_TYPE_NOSNIFF', 'Content type sniffing disabled'),
            ('SECURE_BROWSER_XSS_FILTER', 'XSS filter enabled'),
        ]
        
        for setting, description in ssl_settings:
            if getattr(settings, setting, False):
                self.log_pass('SSL', description)
            else:
                self.log_warning('SSL', f'{description} is disabled')
                
    def check_session_security(self):
        """Check session security settings"""
        print("\n🔑 Checking Session Security...")
        
        session_settings = [
            ('SESSION_COOKIE_SECURE', 'Secure session cookies'),
            ('SESSION_COOKIE_HTTPONLY', 'HttpOnly session cookies'),
            ('SESSION_COOKIE_SAMESITE', 'SameSite session cookies'),
            ('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'Session expires at browser close'),
        ]
        
        for setting, description in session_settings:
            if getattr(settings, setting, False):
                self.log_pass('SESSION', description)
            else:
                self.log_warning('SESSION', f'{description} is disabled')
                
    def check_csrf_protection(self):
        """Check CSRF protection"""
        print("\n🛡️  Checking CSRF Protection...")
        
        if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE:
            self.log_pass('CSRF', 'CSRF middleware is enabled')
        else:
            self.log_issue('CSRF', 'CSRF middleware is disabled', 'CRITICAL')
            
        if hasattr(settings, 'CSRF_TRUSTED_ORIGINS') and settings.CSRF_TRUSTED_ORIGINS:
            self.log_pass('CSRF', 'CSRF trusted origins configured')
        else:
            self.log_warning('CSRF', 'CSRF trusted origins not configured')
            
    def check_xss_protection(self):
        """Check XSS protection"""
        print("\n🚫 Checking XSS Protection...")
        
        if getattr(settings, 'SECURE_BROWSER_XSS_FILTER', False):
            self.log_pass('XSS', 'Browser XSS filter enabled')
        else:
            self.log_warning('XSS', 'Browser XSS filter disabled')
            
        if getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False):
            self.log_pass('XSS', 'Content type sniffing disabled')
        else:
            self.log_warning('XSS', 'Content type sniffing enabled')
            
    def check_file_upload_security(self):
        """Check file upload security"""
        print("\n📁 Checking File Upload Security...")
        
        # Check file upload size limits
        max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 0)
        if max_size > 0:
            self.log_pass('FILE_UPLOAD', f'File upload size limit: {max_size} bytes')
        else:
            self.log_warning('FILE_UPLOAD', 'No file upload size limit configured')
            
        # Check file upload permissions
        permissions = getattr(settings, 'FILE_UPLOAD_PERMISSIONS', None)
        if permissions:
            self.log_pass('FILE_UPLOAD', f'File upload permissions: {oct(permissions)}')
        else:
            self.log_warning('FILE_UPLOAD', 'File upload permissions not configured')
            
    def check_admin_security(self):
        """Check admin panel security"""
        print("\n👨‍💼 Checking Admin Panel Security...")
        
        # Check admin URL
        admin_url = getattr(settings, 'ADMIN_URL', 'admin/')
        if admin_url == 'admin/':
            self.log_warning('ADMIN', 'Using default admin URL - consider changing')
        else:
            self.log_pass('ADMIN', f'Custom admin URL: {admin_url}')
            
        # Check admin users
        admin_users = User.objects.filter(is_superuser=True)
        if admin_users.count() > 5:
            self.log_warning('ADMIN', f'Too many superusers: {admin_users.count()}')
        else:
            self.log_pass('ADMIN', f'Reasonable number of superusers: {admin_users.count()}')
            
        # Check for weak admin passwords
        weak_passwords = []
        for user in admin_users:
            if user.check_password('admin') or user.check_password('password'):
                weak_passwords.append(user.username)
                
        if weak_passwords:
            self.log_issue('ADMIN', f'Weak admin passwords found: {weak_passwords}', 'CRITICAL')
        else:
            self.log_pass('ADMIN', 'No weak admin passwords detected')
            
    def check_api_security(self):
        """Check API security"""
        print("\n🔌 Checking API Security...")
        
        # Check REST framework settings
        if hasattr(settings, 'REST_FRAMEWORK'):
            rf_settings = settings.REST_FRAMEWORK
            
            # Check authentication
            auth_classes = rf_settings.get('DEFAULT_AUTHENTICATION_CLASSES', [])
            if 'rest_framework_simplejwt.authentication.JWTAuthentication' in auth_classes:
                self.log_pass('API', 'JWT authentication enabled')
            else:
                self.log_warning('API', 'JWT authentication not configured')
                
            # Check permissions
            perm_classes = rf_settings.get('DEFAULT_PERMISSION_CLASSES', [])
            if 'rest_framework.permissions.IsAuthenticated' in perm_classes:
                self.log_pass('API', 'Authentication required by default')
            else:
                self.log_warning('API', 'Authentication not required by default')
                
            # Check throttling
            throttle_classes = rf_settings.get('DEFAULT_THROTTLE_CLASSES', [])
            if throttle_classes:
                self.log_pass('API', 'Rate limiting enabled')
            else:
                self.log_warning('API', 'Rate limiting not configured')
        else:
            self.log_warning('API', 'REST framework settings not found')
            
    def check_cors_settings(self):
        """Check CORS settings"""
        print("\n🌐 Checking CORS Settings...")
        
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
            if settings.CORS_ALLOWED_ORIGINS:
                self.log_pass('CORS', 'CORS allowed origins configured')
            else:
                self.log_warning('CORS', 'CORS allowed origins not configured')
        else:
            self.log_warning('CORS', 'CORS settings not found')
            
        if getattr(settings, 'CORS_ALLOW_CREDENTIALS', False):
            self.log_pass('CORS', 'CORS credentials allowed')
        else:
            self.log_warning('CORS', 'CORS credentials not allowed')
            
    def check_logging_security(self):
        """Check logging security"""
        print("\n📝 Checking Logging Security...")
        
        if hasattr(settings, 'LOGGING'):
            self.log_pass('LOGGING', 'Logging configuration found')
            
            # Check for sensitive data in logs
            logging_config = settings.LOGGING
            if 'handlers' in logging_config:
                for handler_name, handler_config in logging_config['handlers'].items():
                    if handler_config.get('class') == 'logging.FileHandler':
                        filename = handler_config.get('filename', '')
                        if filename:
                            self.log_pass('LOGGING', f'File logging configured: {filename}')
        else:
            self.log_warning('LOGGING', 'No logging configuration found')
            
    def check_cache_security(self):
        """Check cache security"""
        print("\n💾 Checking Cache Security...")
        
        if hasattr(settings, 'CACHES'):
            cache_config = settings.CACHES.get('default', {})
            backend = cache_config.get('BACKEND', '')
            
            if 'redis' in backend.lower():
                self.log_pass('CACHE', 'Redis cache backend configured')
            elif 'memcached' in backend.lower():
                self.log_pass('CACHE', 'Memcached cache backend configured')
            else:
                self.log_warning('CACHE', 'Using default cache backend')
        else:
            self.log_warning('CACHE', 'No cache configuration found')
            
    def check_static_files_security(self):
        """Check static files security"""
        print("\n📄 Checking Static Files Security...")
        
        if hasattr(settings, 'STATIC_ROOT'):
            static_root = settings.STATIC_ROOT
            if os.path.exists(static_root):
                self.log_pass('STATIC', f'Static files directory exists: {static_root}')
            else:
                self.log_warning('STATIC', f'Static files directory does not exist: {static_root}')
        else:
            self.log_warning('STATIC', 'STATIC_ROOT not configured')
            
    def check_third_party_security(self):
        """Check third-party integrations security"""
        print("\n🔗 Checking Third-Party Security...")
        
        # Check Stripe configuration
        if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
            if settings.STRIPE_SECRET_KEY.startswith('sk_test_'):
                self.log_warning('STRIPE', 'Using Stripe test keys in production')
            elif settings.STRIPE_SECRET_KEY.startswith('sk_live_'):
                self.log_pass('STRIPE', 'Using Stripe live keys')
            else:
                self.log_warning('STRIPE', 'Stripe secret key format unclear')
        else:
            self.log_warning('STRIPE', 'Stripe secret key not configured')
            
        # Check email configuration
        if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER:
            self.log_pass('EMAIL', 'Email configuration found')
        else:
            self.log_warning('EMAIL', 'Email configuration not found')
            
    def check_code_security(self):
        """Check code-level security"""
        print("\n💻 Checking Code Security...")
        
        # Check for common security issues in views
        views_file = Path('store/views.py')
        if views_file.exists():
            with open(views_file, 'r') as f:
                content = f.read()
                
            # Check for raw SQL queries
            if 'raw(' in content or 'execute(' in content:
                self.log_warning('CODE', 'Raw SQL queries detected in views')
            else:
                self.log_pass('CODE', 'No raw SQL queries detected')
                
            # Check for hardcoded secrets
            if 'password' in content.lower() and '= "' in content:
                self.log_warning('CODE', 'Potential hardcoded passwords detected')
            else:
                self.log_pass('CODE', 'No hardcoded passwords detected')
        else:
            self.log_warning('CODE', 'Views file not found')
            
    def generate_report(self):
        """Generate security audit report"""
        print("\n" + "="*60)
        print("🔒 SECURITY AUDIT REPORT")
        print("="*60)
        
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        total_passed = len(self.passed)
        
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ⚠️  Warnings: {total_warnings}")
        print(f"   ❌ Issues: {total_issues}")
        
        if self.total_checks > 0:
            security_score = (self.score / self.total_checks) * 100
            print(f"   🎯 Security Score: {security_score:.1f}%")
        else:
            security_score = 0
            print(f"   🎯 Security Score: N/A")
            
        # Critical issues
        critical_issues = [issue for issue in self.issues if issue['severity'] == 'CRITICAL']
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(critical_issues)}):")
            for issue in critical_issues:
                print(f"   • {issue['category']}: {issue['message']}")
                
        # High severity issues
        high_issues = [issue for issue in self.issues if issue['severity'] == 'HIGH']
        if high_issues:
            print(f"\n🔴 HIGH PRIORITY ISSUES ({len(high_issues)}):")
            for issue in high_issues:
                print(f"   • {issue['category']}: {issue['message']}")
                
        # Warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:5]:  # Show first 5 warnings
                print(f"   • {warning['category']}: {warning['message']}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more warnings")
                
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if critical_issues:
            print("   • Fix all critical issues immediately")
        if high_issues:
            print("   • Address high priority issues before production")
        if security_score < 80:
            print("   • Improve security score to at least 80%")
        if not self.warnings and not self.issues:
            print("   • Excellent security posture! Keep it up!")
            
        # Production readiness
        if total_issues == 0 and security_score >= 80:
            print(f"\n🚀 PRODUCTION READINESS: READY")
        elif total_issues == 0:
            print(f"\n🚀 PRODUCTION READINESS: READY (with warnings)")
        else:
            print(f"\n🚀 PRODUCTION READINESS: NOT READY")
            
        return {
            'score': security_score,
            'issues': self.issues,
            'warnings': self.warnings,
            'passed': self.passed,
            'ready_for_production': total_issues == 0 and security_score >= 80
        }

def main():
    """Run the security audit"""
    print("🔒 Starting Security Audit for SuperParaguai E-commerce...")
    print("="*60)
    
    auditor = SecurityAuditor()
    
    # Run all security checks
    auditor.check_environment_variables()
    auditor.check_database_security()
    auditor.check_ssl_https_settings()
    auditor.check_session_security()
    auditor.check_csrf_protection()
    auditor.check_xss_protection()
    auditor.check_file_upload_security()
    auditor.check_admin_security()
    auditor.check_api_security()
    auditor.check_cors_settings()
    auditor.check_logging_security()
    auditor.check_cache_security()
    auditor.check_static_files_security()
    auditor.check_third_party_security()
    auditor.check_code_security()
    
    # Generate report
    report = auditor.generate_report()
    
    # Exit with appropriate code
    if report['ready_for_production']:
        print("\n✅ Security audit completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Security audit found issues that need to be addressed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
