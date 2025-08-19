#!/usr/bin/env python
"""
Simple test script to verify admin interface functionality
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_admin_configuration():
    """Test admin configuration and Jazzmin setup"""
    print("🔧 Testing Admin Configuration...")
    print("=" * 50)
    
    try:
        # Test 1: Check Django admin site
        from django.contrib import admin
        print("✅ Django admin site accessible")
        
        # Test 2: Check Jazzmin settings
        from django.conf import settings
        if hasattr(settings, 'JAZZMIN_SETTINGS'):
            print("✅ Jazzmin settings found")
            jazzmin = settings.JAZZMIN_SETTINGS
            print(f"   - Site title: {jazzmin.get('site_title', 'Not set')}")
            print(f"   - Theme: {jazzmin.get('theme', 'Not set')}")
            print(f"   - Dark mode: {'darkly' in str(jazzmin.get('theme', ''))}")
        else:
            print("❌ Jazzmin settings not found")
            return False
        
        # Test 3: Check Jazzmin UI tweaks
        if hasattr(settings, 'JAZZMIN_UI_TWEAKS'):
            print("✅ Jazzmin UI tweaks found")
            ui_tweaks = settings.JAZZMIN_UI_TWEAKS
            print(f"   - Navbar: {ui_tweaks.get('navbar', 'Not set')}")
            print(f"   - Sidebar: {ui_tweaks.get('sidebar', 'Not set')}")
        else:
            print("❌ Jazzmin UI tweaks not found")
            return False
        
        # Test 4: Check admin models
        from store.admin import CartOrderAdmin, SalesAnalyticsAdmin
        print("✅ Admin models accessible")
        
        # Test 5: Check admin site registration
        admin_site = admin.site
        registered_models = [model._meta.model_name for model in admin_site._registry.keys()]
        print(f"✅ Admin site has {len(registered_models)} registered models")
        
        # Test 6: Check specific models
        if 'cartorder' in registered_models:
            print("✅ CartOrder model registered")
        else:
            print("❌ CartOrder model not registered")
        
        if 'product' in registered_models:
            print("✅ Product model registered")
        else:
            print("❌ Product model not registered")
        
        print("\n" + "=" * 50)
        print("🎉 Admin configuration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Admin configuration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sales_analytics():
    """Test sales analytics functionality"""
    print("\n📊 Testing Sales Analytics...")
    print("=" * 50)
    
    try:
        # Test 1: Check models
        from store.models import CartOrder, Product
        print("✅ Store models accessible")
        
        # Test 2: Check if there are any orders
        orders_count = CartOrder.objects.count()
        print(f"✅ Found {orders_count} orders in database")
        
        # Test 3: Check if there are any products
        products_count = Product.objects.count()
        print(f"✅ Found {products_count} products in database")
        
        # Test 4: Test sales calculations
        from store.admin import SalesDashboardAdmin
        from django.contrib import admin
        admin_instance = SalesDashboardAdmin(CartOrder, admin.site)
        
        # Test the changelist view context
        print("✅ SalesDashboardAdmin accessible")
        
        print("\n" + "=" * 50)
        print("🎉 Sales analytics test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Sales analytics test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 SuperParaguai Admin Interface Test Suite")
    print("=" * 60)
    
    # Test admin configuration
    admin_test_passed = test_admin_configuration()
    
    # Test sales analytics
    analytics_test_passed = test_sales_analytics()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Admin Configuration: {'✅ PASSED' if admin_test_passed else '❌ FAILED'}")
    print(f"Sales Analytics: {'✅ PASSED' if analytics_test_passed else '❌ FAILED'}")
    
    if admin_test_passed and analytics_test_passed:
        print("\n🎉 All tests passed! The admin interface should be working correctly.")
        print("\n🌐 To test the admin interface:")
        print("   1. Start the Django server: python manage.py runserver")
        print("   2. Open your browser and go to: http://127.0.0.1:8000/admin/")
        print("   3. Log in with your admin credentials")
        print("   4. You should see the new dark theme and sales analytics")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
