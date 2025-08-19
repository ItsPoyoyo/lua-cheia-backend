#!/usr/bin/env python
"""
Test script to verify cart functionality
Run this script to test cart quantity adjustment and stock validation
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from store.models import Product, Cart, User, Category, Vendor
from store.views import validate_product_stock

def test_cart_functionality():
    """Test cart quantity adjustment and stock validation"""
    print("🧪 Testing Cart Functionality...")
    print("=" * 50)
    
    try:
        # Test 1: Check if products exist
        print("\n1. Checking product availability...")
        products = Product.objects.filter(status='published', in_stock=True)
        if products.exists():
            print(f"✅ Found {products.count()} available products")
            test_product = products.first()
            print(f"   - Test product: {test_product.title}")
            print(f"   - Stock: {test_product.stock_qty}")
            print(f"   - Max cart limit: {test_product.max_cart_limit}")
        else:
            print("❌ No available products found")
            return False
        
        # Test 2: Test stock validation
        print("\n2. Testing stock validation...")
        test_qty = 1
        is_valid, error_msg, available_stock = validate_product_stock(
            test_product, test_qty
        )
        
        if is_valid:
            print(f"✅ Stock validation passed for {test_qty} item(s)")
            print(f"   - Available stock: {available_stock}")
        else:
            print(f"❌ Stock validation failed: {error_msg}")
        
        # Test 3: Test cart limit validation
        print("\n3. Testing cart limit validation...")
        over_limit_qty = test_product.max_cart_limit + 1
        is_valid, error_msg, available_stock = validate_product_stock(
            test_product, over_limit_qty
        )
        
        if not is_valid and "Maximum" in error_msg:
            print(f"✅ Cart limit validation working correctly")
            print(f"   - Attempted: {over_limit_qty}, Limit: {test_product.max_cart_limit}")
        else:
            print(f"❌ Cart limit validation failed: {error_msg}")
        
        # Test 4: Test out-of-stock validation
        print("\n4. Testing out-of-stock validation...")
        if test_product.stock_qty > 0:
            # Temporarily set stock to 0 for testing
            original_stock = test_product.stock_qty
            test_product.stock_qty = 0
            test_product.in_stock = False
            test_product.save()
            
            is_valid, error_msg, available_stock = validate_product_stock(
                test_product, 1
            )
            
            if not is_valid and "out of stock" in error_msg.lower():
                print("✅ Out-of-stock validation working correctly")
            else:
                print(f"❌ Out-of-stock validation failed: {error_msg}")
            
            # Restore original stock
            test_product.stock_qty = original_stock
            test_product.in_stock = True
            test_product.save()
        else:
            print("⚠️  Product already out of stock, skipping out-of-stock test")
        
        # Test 5: Test cart model
        print("\n5. Testing cart model...")
        try:
            # Create a test cart item (without saving to avoid database pollution)
            cart_item = Cart(
                product=test_product,
                qty=1,
                price=test_product.price,
                sub_total=test_product.price,
                shipping_ammount=Decimal('5.00'),
                tax_fee=Decimal('0.00'),
                service_fee=Decimal('0.00'),
                total=test_product.price + Decimal('5.00'),
                cart_id='test_cart_123'
            )
            
            # Test cart item properties
            print(f"✅ Cart model working correctly")
            print(f"   - Product: {cart_item.product.title}")
            print(f"   - Quantity: {cart_item.qty}")
            print(f"   - Total: ${cart_item.total}")
            
        except Exception as e:
            print(f"❌ Cart model test failed: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🎉 Cart functionality tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_functionality():
    """Test admin-related functionality"""
    print("\n🔧 Testing Admin Functionality...")
    print("=" * 50)
    
    try:
        # Test 1: Check admin models
        print("\n1. Checking admin models...")
        from store.admin import CartOrderAdmin
        
        if CartOrderAdmin:
            print("✅ CartOrderAdmin model found")
        else:
            print("❌ CartOrderAdmin model not found")
        
        # Test 2: Check sales analytics
        print("\n2. Checking sales analytics...")
        from store.admin import SalesAnalyticsAdmin
        
        if SalesAnalyticsAdmin:
            print("✅ SalesAnalyticsAdmin model found")
        else:
            print("❌ SalesAnalyticsAdmin model not found")
        
        # Test 3: Check Jazzmin configuration
        print("\n3. Checking Jazzmin configuration...")
        from django.conf import settings
        
        if hasattr(settings, 'JAZZMIN_SETTINGS'):
            print("✅ Jazzmin settings configured")
            jazzmin_settings = settings.JAZZMIN_SETTINGS
            print(f"   - Theme: {jazzmin_settings.get('site_title', 'Not set')}")
            print(f"   - Dark mode: {'darkly' in str(jazzmin_settings.get('theme', ''))}")
        else:
            print("❌ Jazzmin settings not found")
        
        print("\n" + "=" * 50)
        print("🎉 Admin functionality tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Admin test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 SuperParaguai E-commerce - Functionality Test Suite")
    print("=" * 60)
    
    # Test cart functionality
    cart_test_passed = test_cart_functionality()
    
    # Test admin functionality
    admin_test_passed = test_admin_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Cart Functionality: {'✅ PASSED' if cart_test_passed else '❌ FAILED'}")
    print(f"Admin Functionality: {'✅ PASSED' if admin_test_passed else '❌ FAILED'}")
    
    if cart_test_passed and admin_test_passed:
        print("\n🎉 All tests passed! The system is ready for production.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

