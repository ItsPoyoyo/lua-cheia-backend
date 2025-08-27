from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
from decimal import Decimal
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

# Admin imports
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta

# Models
from userauths.models import User
from store.models import (
    Coupon, Product, Tax, Category, Review, Cart, Size, Color, 
    CartOrder, CartOrderItem, Notification, OffersCarousel, Banner, CarouselImage
)

# Serializers
from store.serializers import (
    CartSerializer, ReviewSerializer, CategorySerializer, 
    CartOrderItemSerializer, ProductSerializer, CartOrderSerializer, 
    CouponSerializer, NotificationSerializer, OffersCarouselSerializer, 
    BannerSerializer, CarouselImageSerializer
)

# Rest Framework
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view

def send_notification(user=None, vendor=None, order=None, order_item=None):
    Notification.objects.create(
        user=user,
        vendor=vendor,
        order=order,
        order_item=order_item,
    )

class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Only return published products that are in stock
        return Product.objects.filter(
            status='published',
            in_stock=True
        ).select_related('category', 'vendor').prefetch_related('colors', 'sizes')
    
class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        identifier = self.kwargs['slug']
        
        # Try to find by ID first (numeric)
        if identifier.isdigit():
            try:
                product = Product.objects.get(id=int(identifier))
            except Product.DoesNotExist:
                raise Http404("Product not found")
        else:
            # Try to find by slug
            try:
                product = Product.objects.get(slug=identifier)
            except Product.DoesNotExist:
                raise Http404("Product not found")
        
        # Increment view count
        product.views += 1
        product.save()
        return product

class CartAPIView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    queryset = Cart.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            payload = request.data
            print(f"DEBUG: CartAPIView - Received payload: {payload}")
            
            product_id = payload.get('product_id') or payload.get('product')
            user_id = payload.get('user_id') or payload.get('user')
            qty = int(payload.get('qty', 1))
            price = Decimal(payload.get('price', 0))
            shipping_ammount = Decimal(payload.get('shipping_ammount', 0) or payload.get('shipping_amount', 0))
            country = payload.get('country')
            size = payload.get('size')
            color = payload.get('color')
            cart_id = payload.get('cart_id')
            
            print(f"DEBUG: CartAPIView - Parsed values: product_id={product_id}, user_id={user_id}, cart_id={cart_id}")

            # Validate required fields
            if not product_id:
                return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not cart_id:
                return Response({"error": "Cart ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if qty <= 0:
                return Response({"error": "Quantity must be greater than 0"}, status=status.HTTP_400_BAD_REQUEST)

            # Get product and validate it exists and is published
            try:
                product = Product.objects.get(status="published", id=product_id)
            except Product.DoesNotExist:
                return Response({"error": "Product not found or not available"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if product is in stock
            if product.stock_qty <= 0:
                return Response(
                    {"error": f"Product '{product.title}' is out of stock"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if requested quantity exceeds product stock
            if qty > product.stock_qty:
                return Response(
                    {"error": f"Only {product.stock_qty} available in stock for '{product.title}'. You requested {qty}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if requested quantity exceeds max cart limit
            if qty > product.max_cart_limit:
                return Response(
                    {"error": f"Maximum cart limit for '{product.title}' is {product.max_cart_limit}. You requested {qty}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate color selection if product has colors
            product_colors = product.color()
            if product_colors.exists():
                if not color or color == "No Color":
                    return Response(
                        {"error": f"Please select a color for '{product.title}'. Available colors: {', '.join([c.name for c in product_colors])}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if selected color exists and has stock
                color_obj = product_colors.filter(name=color).first()
                if not color_obj:
                    return Response(
                        {"error": f"Color '{color}' is not available for '{product.title}'. Available colors: {', '.join([c.name for c in product_colors])}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if color_obj.stock_qty < qty:
                    return Response(
                        {"error": f"Only {color_obj.stock_qty} available in stock for color '{color}' of '{product.title}'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Product has no colors, ensure color is set to "No Color"
                color = "No Color"
            
            # Validate size selection if product has sizes
            product_sizes = product.size()
            if product_sizes.exists():
                if not size or size == "No Size":
                    return Response(
                        {"error": f"Please select a size for '{product.title}'. Available sizes: {', '.join([s.name for s in product_sizes])}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if selected size exists and has stock
                size_obj = product_sizes.filter(name=size).first()
                if not size_obj:
                    return Response(
                        {"error": f"Size '{size}' is not available for '{product.title}'. Available sizes: {', '.join([s.name for c in product_sizes])}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if size_obj.stock_qty < qty:
                    return Response(
                        {"error": f"Only {size_obj.stock_qty} available in stock for size '{size}' of '{product.title}'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Product has no sizes, ensure size is set to "No Size"
                size = "No Size"

            user = User.objects.get(id=user_id) if user_id and user_id != 'undefined' else None
            tax = Tax.objects.filter(country=country).first()
            tax_rate = tax.rate / 100 if tax else 0

            sub_total = price * qty
            shipping_total = shipping_ammount * qty
            tax_fee = sub_total * Decimal(tax_rate)
            service_fee = sub_total * Decimal(0.01)
            total = sub_total + shipping_total + tax_fee + service_fee

            # Check if cart item already exists with same product, color, and size
            existing_cart = Cart.objects.filter(
                cart_id=cart_id, 
                product=product, 
                color=color, 
                size=size
            ).first()
            
            if existing_cart:
                # Update existing cart item quantity
                new_qty = existing_cart.qty + qty
                
                # Check if new total quantity exceeds stock limits
                if new_qty > product.stock_qty:
                    return Response(
                        {"error": f"Cannot add {qty} more. Total quantity would exceed available stock ({product.stock_qty})"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if new_qty > product.max_cart_limit:
                    return Response(
                        {"error": f"Cannot add {qty} more. Total quantity would exceed cart limit ({product.max_cart_limit})"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update existing cart item
                existing_cart.qty = new_qty
                existing_cart.sub_total = price * new_qty
                existing_cart.shipping_ammount = shipping_ammount * new_qty
                existing_cart.tax_fee = existing_cart.sub_total * Decimal(tax_rate)
                existing_cart.service_fee = existing_cart.sub_total * Decimal(0.01)
                existing_cart.total = existing_cart.sub_total + existing_cart.shipping_ammount + existing_cart.tax_fee + existing_cart.service_fee
                existing_cart.save()
                
                return Response(
                    {'message': f"Cart Updated Successfully. Total quantity: {new_qty}"},
                    status=status.HTTP_200_OK
                )
            else:
                # Create new cart item
                cart = Cart()
                cart.product = product
                cart.user = user
                cart.qty = qty
                cart.price = price
                cart.sub_total = sub_total
                cart.shipping_ammount = shipping_total
                cart.tax_fee = tax_fee
                cart.color = color
                cart.size = size
                cart.country = country
                cart.cart_id = cart_id
                cart.service_fee = service_fee
                cart.total = total
                cart.save()
                
                return Response(
                    {'message': "Cart Created Successfully"},
                    status=status.HTTP_201_CREATED
                )

        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CartListView(generics.ListAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        try:
            cart_id = self.kwargs['cart_id']
            user_id = self.kwargs.get('user_id')
            
            print(f"DEBUG: CartListView.get_queryset - cart_id: {cart_id}, user_id: {user_id}")
            
            if user_id is not None:
                try:
                    user = User.objects.get(id=user_id)
                    queryset = Cart.objects.filter(user=user, cart_id=cart_id)
                except User.DoesNotExist:
                    print(f"DEBUG: User {user_id} not found")
                    return []
            else:
                queryset = Cart.objects.filter(cart_id=cart_id)
            
            print(f"DEBUG: CartListView.get_queryset - initial queryset count: {queryset.count()}")
            
            # Filter out invalid cart items (products that are no longer available)
            valid_cart_items = []
            for cart_item in queryset:
                try:
                    print(f"DEBUG: Processing cart item {cart_item.id} - product: {cart_item.product.title if cart_item.product else 'None'}")
                    
                    # Check if product still exists and is published
                    if (cart_item.product and 
                        cart_item.product.status == 'published' and 
                        cart_item.product.stock_qty > 0):
                        
                        # Check if color still exists and has stock
                        if cart_item.color and cart_item.color != "No Color":
                            try:
                                color_obj = cart_item.product.color().filter(name=cart_item.color).first()
                                if not color_obj or color_obj.stock_qty < cart_item.qty:
                                    print(f"DEBUG: Color {cart_item.color} out of stock or not found")
                                    continue  # Skip this item
                            except Exception as color_error:
                                print(f"DEBUG: Error checking color {cart_item.color}: {color_error}")
                                continue
                        
                        # Check if size still exists and has stock
                        if cart_item.size and cart_item.size != "No Size":
                            try:
                                size_obj = cart_item.product.size().filter(name=cart_item.size).first()
                                if not size_obj or size_obj.stock_qty < cart_item.qty:
                                    print(f"DEBUG: Size {cart_item.size} out of stock or not found")
                                    continue  # Skip this item
                            except Exception as size_error:
                                print(f"DEBUG: Error checking size {cart_item.size}: {size_error}")
                                continue
                        
                        # Check if quantity doesn't exceed current stock
                        if cart_item.qty <= cart_item.product.stock_qty:
                            valid_cart_items.append(cart_item)
                        else:
                            # Adjust quantity to available stock
                            cart_item.qty = cart_item.product.stock_qty
                            cart_item.save()
                            valid_cart_items.append(cart_item)
                            
                    else:
                        # Product is no longer valid, delete the cart item
                        print(f"DEBUG: Product {cart_item.product.title if cart_item.product else 'None'} is invalid, deleting cart item")
                        cart_item.delete()
                        
                except Exception as e:
                    print(f"DEBUG: Error validating cart item {cart_item.id}: {e}")
                    # Delete invalid cart item
                    cart_item.delete()
            
            print(f"DEBUG: CartListView.get_queryset - valid_cart_items count: {len(valid_cart_items)}")
            return valid_cart_items
            
        except Exception as e:
            print(f"DEBUG: CartListView.get_queryset - Critical error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def list(self, request, *args, **kwargs):
        try:
            print(f"DEBUG: CartListView.list - Starting...")
            queryset = self.get_queryset()
            print(f"DEBUG: CartListView.list - Got queryset, length: {len(queryset)}")
            
            serializer = self.get_serializer(queryset, many=True)
            print(f"DEBUG: CartListView.list - Got serializer data")
            
            # Debug logging
            print(f"DEBUG: CartListView - cart_id: {self.kwargs.get('cart_id')}")
            print(f"DEBUG: CartListView - user_id: {self.kwargs.get('user_id')}")
            print(f"DEBUG: CartListView - valid_cart_items count: {len(queryset)}")
            print(f"DEBUG: CartListView - serializer data: {serializer.data}")
            
            # Calculate totals
            totals = {
                'shipping': 0.0,
                'tax': 0.0,
                'service_fee': 0.0,
                'sub_total': 0.0,
                'total': 0.0,
            }

            for cart_item in queryset:
                totals['shipping'] += float(cart_item.shipping_ammount)
                totals['tax'] += float(cart_item.tax_fee)
                totals['service_fee'] += float(cart_item.service_fee)
                totals['sub_total'] += float(cart_item.sub_total)
                totals['total'] += float(cart_item.total)

            response_data = {
                'cart_items': serializer.data,
                'cart_total': totals
            }
            
            print(f"DEBUG: CartListView - response data: {response_data}")
            print(f"DEBUG: CartListView.list - Successfully returning response")
            
            return Response(response_data)
            
        except Exception as e:
            print(f"DEBUG: CartListView.list - Critical error: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

class CartDetailView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    lookup_field = "cart_id"

    def get_queryset(self):
        cart_id = self.kwargs['cart_id']
        user_id = self.kwargs.get('user_id')   
        if user_id is not None:
            user = User.objects.get(id=user_id)
            return Cart.objects.filter(user=user, cart_id=cart_id)
        return Cart.objects.filter(cart_id=cart_id)
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        totals = {
            'shipping': 0.0,
            'tax': 0.0,
            'service_fee': 0.0,
            'sub_total': 0.0,
            'total': 0.0,
        }

        for cart_item in queryset:
            totals['shipping'] += float(cart_item.shipping_ammount)
            totals['tax'] += float(cart_item.tax_fee)
            totals['service_fee'] += float(cart_item.service_fee)
            totals['sub_total'] += float(cart_item.sub_total)
            totals['total'] += float(cart_item.total)

        return Response(totals)

class CartUpdateAPIView(generics.UpdateAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        cart_id = self.kwargs['cart_id']
        item_id = self.kwargs['item_id']
        print(f"DEBUG: CartUpdateAPIView - Looking for cart_id: {cart_id}, item_id: {item_id}")
        
        try:
            cart_item = Cart.objects.get(cart_id=cart_id, id=item_id)
            print(f"DEBUG: CartUpdateAPIView - Found cart item: {cart_item}")
            return cart_item
        except Cart.DoesNotExist:
            print(f"DEBUG: CartUpdateAPIView - Cart item not found for cart_id: {cart_id}, item_id: {item_id}")
            raise
        except Exception as e:
            print(f"DEBUG: CartUpdateAPIView - Error getting cart item: {e}")
            raise

    def update(self, request, *args, **kwargs):
        try:
            cart_item = self.get_object()
            
            print(f"DEBUG: CartUpdateAPIView - Updating cart item {cart_item.id}")
            print(f"DEBUG: CartUpdateAPIView - Request data: {request.data}")
            
            # Update quantity
            if 'qty' in request.data:
                new_qty = int(request.data['qty'])
                print(f"DEBUG: CartUpdateAPIView - New quantity: {new_qty}")
                
                # Validate quantity
                if new_qty <= 0:
                    return Response(
                        {"error": "Quantity must be greater than 0"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if new_qty > cart_item.product.max_cart_limit:
                    return Response(
                        {"error": f"Quantity cannot exceed {cart_item.product.max_cart_limit}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check stock availability
                if new_qty > cart_item.product.stock_qty:
                    return Response(
                        {"error": f"Only {cart_item.product.stock_qty} available in stock for '{cart_item.product.title}'"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check max cart limit
                if new_qty > cart_item.product.max_cart_limit:
                    return Response(
                        {"error": f"Maximum cart limit for '{cart_item.product.title}' is {cart_item.product.max_cart_limit}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check color stock if applicable
                if cart_item.color and cart_item.color != "No Color":
                    color_obj = cart_item.product.color().filter(name=cart_item.color).first()
                    if color_obj and new_qty > color_obj.stock_qty:
                        return Response(
                            {"error": f"Only {color_obj.stock_qty} available in stock for color '{cart_item.color}' of '{cart_item.product.title}'"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Check size stock if applicable
                if cart_item.size and cart_item.size != "No Size":
                    size_obj = cart_item.product.size().filter(name=cart_item.size).first()
                    if size_obj and new_qty > size_obj.stock_qty:
                        return Response(
                            {"error": f"Only {size_obj.stock_qty} available in stock for size '{cart_item.size}' of '{cart_item.product.title}'"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Update quantity and recalculate totals
                cart_item.qty = new_qty
                cart_item.sub_total = cart_item.price * new_qty
                
                # Get shipping amount from the product and multiply by new quantity
                shipping_per_item = cart_item.product.shipping_ammount
                cart_item.shipping_ammount = shipping_per_item * new_qty
                
                # Calculate tax and service fees based on sub_total
                cart_item.tax_fee = cart_item.sub_total * Decimal(0.1)  # Assuming 10% tax rate
                cart_item.service_fee = cart_item.sub_total * Decimal(0.01)  # 1% service fee
                cart_item.total = cart_item.sub_total + cart_item.shipping_ammount + cart_item.tax_fee + cart_item.service_fee
                
                cart_item.save()
                
                print(f"DEBUG: CartUpdateAPIView - Cart item updated successfully")
                print(f"DEBUG: CartUpdateAPIView - New totals: qty={cart_item.qty}, sub_total={cart_item.sub_total}, total={cart_item.total}")
                
                return Response({
                    "message": "Cart updated successfully",
                    "cart_item": CartSerializer(cart_item).data
                })
            
            return Response(
                {"error": "No valid fields to update"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"DEBUG: CartUpdateAPIView - Error in update method: {e}")
            return Response(
                {"error": f"Error updating cart: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CartItemDeleteAPIView(generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        item_id = self.kwargs['item_id']
        cart_id = self.kwargs.get('cart_id')
        user_id = self.kwargs.get('user_id')
        
        print(f"DEBUG: CartItemDeleteAPIView - Deleting item_id: {item_id}, cart_id: {cart_id}, user_id: {user_id}")
        
        try:
            cart_item = Cart.objects.get(id=item_id)
            print(f"DEBUG: Found cart item: {cart_item.product.title}, qty: {cart_item.qty}")
            return cart_item
        except Cart.DoesNotExist:
            print(f"DEBUG: Cart item {item_id} not found")
            raise
        except Exception as e:
            print(f"DEBUG: Error getting cart item: {e}")
            raise

    def perform_destroy(self, instance):
        try:
            print(f"DEBUG: Deleting cart item {instance.id} for product {instance.product.title}")
            print(f"DEBUG: Current product stock: {instance.product.stock_qty}")
            print(f"DEBUG: Cart item quantity: {instance.qty}")
            
            # Only restore stock if this cart item was part of a completed order
            # For WhatsApp orders that haven't been paid yet, we shouldn't restore stock
            # since it was never reduced in the first place
            
            # Check if this cart item belongs to a completed order
            # We need to check through CartOrderItem since CartOrder doesn't have cart_id
            completed_orders = CartOrder.objects.filter(
                orderitem__product=instance.product,
                orderitem__color=instance.color,
                orderitem__size=instance.size,
                payment_status='paid'
            )
            
            if completed_orders.exists():
                print(f"DEBUG: Cart item belongs to completed order, restoring stock")
                # Restore stock only if it was actually reduced
                instance.product.stock_qty += instance.qty
                instance.product.save()
                print(f"DEBUG: Stock restored to: {instance.product.stock_qty}")
            else:
                print(f"DEBUG: Cart item does not belong to completed order, not restoring stock")
            
            instance.delete()
            print(f"DEBUG: Cart item deleted successfully")
            
        except Exception as e:
            print(f"DEBUG: Error deleting cart item: {e}")
            # Still delete the cart item even if stock restoration fails
            instance.delete()
            raise e

class createOrderAPIView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    queryset = CartOrder.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data
        with transaction.atomic():
            try:
                # Create order
                payment_method = payload.get('payment_method', 'stripe')
                print(f"DEBUG: Creating order with payment_method: {payment_method}")
                
                order = CartOrder.objects.create(
                    buyer=User.objects.get(id=payload['user_id']) if payload['user_id'] != 0 else None,
                    payment_status="pending",
                    full_name=payload['full_name'],
                    email=payload['email'],
                    phone=payload['phone'],
                    address=payload['address'],
                    city=payload['city'],
                    state=payload['state'],
                    country=payload['country'],
                    payment_method=payment_method
                )
                
                print(f"DEBUG: Order created with ID: {order.oid}, payment_method: {order.payment_method}")

                cart_items = Cart.objects.filter(cart_id=payload['cart_id'])
                totals = {
                    'shipping': Decimal(0.0),
                    'tax': Decimal(0.0),
                    'service_fee': Decimal(0.0),
                    'sub_total': Decimal(0.0),
                    'total': Decimal(0.0),
                }

                for cart_item in cart_items:
                    product = Product.objects.select_for_update().get(id=cart_item.product.id)
                    
                    # Check product stock
                    if product.stock_qty < cart_item.qty:
                        raise Exception(f"Not enough stock for {product.title}. Available: {product.stock_qty}")
                    
                    # Check color stock if specified
                    if cart_item.color and cart_item.color != "No Color":
                        color = Color.objects.select_for_update().filter(
                            product=product, 
                            name=cart_item.color
                        ).first()
                        if not color or color.stock_qty < cart_item.qty:
                            raise Exception(f"Not enough stock for color {cart_item.color}")
                    
                    # Check size stock if specified
                    if cart_item.size and cart_item.size != "No Size":
                        size = Size.objects.select_for_update().filter(
                            product=product, 
                            name=cart_item.size
                        ).first()
                        if not size or size.stock_qty < cart_item.qty:
                            raise Exception(f"Not enough stock for size {cart_item.size}")

                    # Create order item
                    print(f"DEBUG: Creating order item for product: {product.title}")
                    print(f"DEBUG: Cart item color: '{cart_item.color}', size: '{cart_item.size}'")
                    print(f"DEBUG: Cart item qty: {cart_item.qty}")
                    
                    order_item = CartOrderItem.objects.create(
                        order=order,
                        product=product,
                        qty=cart_item.qty,
                        color=cart_item.color,
                        size=cart_item.size,
                        price=cart_item.price,
                        sub_total=cart_item.sub_total,
                        shipping_ammount=cart_item.shipping_ammount,
                        tax_fee=cart_item.tax_fee,
                        service_fee=cart_item.service_fee,
                        total=cart_item.total,
                        initial_total=cart_item.total,
                        vendor=product.vendor
                    )
                    
                    print(f"DEBUG: Order item created with ID: {order_item.id}")
                    print(f"DEBUG: Order item color: '{order_item.color}', size: '{order_item.size}'")

                    # Update product stock ONLY for non-WhatsApp orders
                    # WhatsApp orders will reduce stock when admin marks payment as PAID
                    if order.payment_method != 'whatsapp':
                        print(f"DEBUG: Reducing stock for non-WhatsApp order. Product: {product.title}, Qty: {cart_item.qty}")
                        product.stock_qty -= cart_item.qty
                        product.save()
                        
                        # Update color stock if specified
                        if cart_item.color and cart_item.color != "No Color" and color:
                            color.stock_qty -= cart_item.qty
                            color.save()
                        
                        # Update size stock if specified
                        if cart_item.size and cart_item.size != "No Size" and size:
                            size.stock_qty -= cart_item.qty
                            size.save()
                    else:
                        print(f"DEBUG: WhatsApp order - NOT reducing stock. Product: {product.title}, Qty: {cart_item.qty}")

                    # Update totals
                    totals['shipping'] += Decimal(cart_item.shipping_ammount)
                    totals['tax'] += Decimal(cart_item.tax_fee)
                    totals['service_fee'] += Decimal(cart_item.service_fee)
                    totals['sub_total'] += Decimal(cart_item.sub_total)
                    totals['total'] += Decimal(cart_item.total)

                    order.vendor.add(product.vendor)

                # Update order totals
                order.sub_total = totals['sub_total']
                order.shipping_ammount = totals['shipping']
                order.tax_fee = totals['tax']
                order.service_fee = totals['service_fee']
                order.total = totals['total']
                order.save()

                # Clear cart
                print(f"DEBUG: Clearing cart items for cart_id: {payload['cart_id']}")
                deleted_count = cart_items.delete()
                print(f"DEBUG: Deleted {deleted_count[0]} cart items")

                return Response(
                    {"message": "Order Created Successfully", "order_oid": order.oid},
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

class CheckoutView(generics.RetrieveUpdateAPIView):
    serializer_class = CartOrderSerializer
    lookup_field = 'order_oid'
    permission_classes = [AllowAny]

    def get_object(self):
        order_oid = self.kwargs['order_oid']
        return CartOrder.objects.get(oid=order_oid)
    
    def patch(self, request, *args, **kwargs):
        """Update order payment method"""
        order = self.get_object()
        payment_method = request.data.get('payment_method')
        
        if payment_method and payment_method in ['stripe', 'whatsapp']:
            order.payment_method = payment_method
            order.save()
            
            return Response({
                "message": f"Order payment method updated to {payment_method}",
                "payment_method": payment_method
            })
        else:
            return Response({
                "error": "Invalid payment method. Must be 'stripe' or 'whatsapp'"
            }, status=status.HTTP_400_BAD_REQUEST)

class CouponAPIView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    queryset = Coupon.objects.all()
    permission_classes = [AllowAny]

    def create(self, request):
        payload = request.data
        order_oid = payload['order_oid']
        coupon_code = payload['coupon_code']

        order = CartOrder.objects.get(oid=order_oid)
        coupon = Coupon.objects.filter(code=coupon_code).first()

        if not coupon:
            return Response({"message": "Coupon Does Not Exist", "icon": "error"})

        order_items = CartOrderItem.objects.filter(order=order, vendor=coupon.vendor)
        if not order_items:
            return Response({"message": "Order Item Does Not Exist", "icon": "error"})

        for item in order_items:
            if coupon in item.coupon.all():
                return Response({"message": "Coupon Already Activated", "icon": "warning"})

            discount = item.total * coupon.discount / 100
            item.total -= discount
            item.sub_total -= discount
            item.coupon.add(coupon)
            item.saved += discount
            item.save()

            order.total -= discount
            order.sub_total -= discount
            order.saved += discount
            order.save()

        return Response({"message": "Coupon Activated", "icon": "success"})

class StripeCheckoutView(generics.CreateAPIView):
    """
    Creates a Stripe Checkout session for an order
    """
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        order_oid = self.kwargs['order_oid']
        
        try:
            # Debug: Print Stripe configuration status
            print(f"DEBUG: Stripe Secret Key exists: {bool(settings.STRIPE_SECRET_KEY)}")
            print(f"DEBUG: Stripe Secret Key length: {len(settings.STRIPE_SECRET_KEY) if settings.STRIPE_SECRET_KEY else 0}")
            
            # Check if Stripe is configured
            if not settings.STRIPE_SECRET_KEY:
                return Response(
                    {"error": "Stripe is not configured. Please set STRIPE_SECRET_KEY."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Debug: Print order lookup info
            print(f"DEBUG: Looking for order with OID: {order_oid}")
            
            order = CartOrder.objects.select_related('buyer').get(oid=order_oid)
            print(f"DEBUG: Order found - ID: {order.id}, Status: {order.payment_status}")
            
            # Early return if already paid
            if order.payment_status == 'paid':
                return Response(
                    {"message": "Order already paid"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get order items and validate
            print(f"DEBUG: Getting order items for order {order.id}")
            order_items = order.orderitem.all()
            print(f"DEBUG: Found {order_items.count()} order items")
            
            if not order_items.exists():
                return Response(
                    {"error": "Order has no items to process"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate required order fields
            print(f"DEBUG: Order phone: '{order.phone}'")
            print(f"DEBUG: Order email: '{order.email}'")
            print(f"DEBUG: Order full_name: '{order.full_name}'")
            
            if not order.phone or order.phone.strip() == '':
                return Response(
                    {"error": "Phone number is required for checkout"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not order.email or order.email.strip() == '':
                return Response(
                    {"error": "Email is required for checkout"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create line items from order items
            print(f"DEBUG: Creating line items from {order_items.count()} order items")
            line_items = []
            for item in order_items:
                print(f"DEBUG: Processing order item {item.id} - Product: {item.product.title if item.product else 'None'}, Price: {item.price}, Qty: {item.qty}")
                
                if not item.product:
                    return Response(
                        {"error": f"Order item {item.id} has no associated product"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': item.product.title,
                        },
                        'unit_amount': int(item.price * 100),  # Convert to cents
                    },
                    'quantity': item.qty,
                })
            
            print(f"DEBUG: Created {len(line_items)} line items")

            # Validate line items
            if not line_items:
                return Response(
                    {"error": "No valid line items to process"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            print(f"DEBUG: About to create Stripe checkout session")
            print(f"DEBUG: Line items: {line_items}")
            print(f"DEBUG: Customer email: {order.email}")
            print(f"DEBUG: Success URL: {settings.FRONTEND_URL}/payment-success/{order.oid}/")
            
            try:
                checkout_session = stripe.checkout.Session.create(
                    customer_email=order.email,
                    payment_method_types=['card'],
                    line_items=line_items,
                    mode='payment',
                    success_url=(
                        f'{settings.FRONTEND_URL}/payment-success/{order.oid}/'
                        f'?session_id={{CHECKOUT_SESSION_ID}}'
                    ),
                    cancel_url=f'{settings.FRONTEND_URL}/payment-failed/',
                    metadata={
                        'order_oid': order.oid,
                        'buyer_id': str(order.buyer.id) if order.buyer else ''
                    },
                    expires_at=int((timezone.now() + timezone.timedelta(hours=1)).timestamp())
                )
                print(f"DEBUG: Stripe checkout session created successfully: {checkout_session.id}")
            except stripe.error.StripeError as stripe_error:
                print(f"DEBUG: Stripe API error: {stripe_error}")
                print(f"DEBUG: Stripe error type: {type(stripe_error)}")
                raise stripe_error
            except Exception as other_error:
                print(f"DEBUG: Other error during Stripe session creation: {other_error}")
                print(f"DEBUG: Error type: {type(other_error)}")
                print(f"DEBUG: Error traceback:")
                import traceback
                traceback.print_exc()
                raise other_error

            # Update order with session info
            order.stripe_sesion_id = checkout_session.id  # Note: field name has typo in model
            order.save(update_fields=['stripe_sesion_id'])

            return Response({
                'url': checkout_session.url,
                'session_id': checkout_session.id
            })

        except CartOrder.DoesNotExist:
            return Response(
                {"message": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return Response(
                {"error": f"Server error: {str(e)}", "details": error_details},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentSuccessView(generics.CreateAPIView):
    """
    Handles payment verification and post-payment processing
    """
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data
        order_oid = payload.get('order_oid')
        session_id = payload.get('session_id')

        # Input validation
        if not order_oid or not session_id:
            return Response(
                {"message": "Missing order_oid or session_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch order with related data in single query
            order = CartOrder.objects.select_related('buyer').prefetch_related(
                'orderitem', 'orderitem__vendor', 'orderitem__product'
            ).get(oid=order_oid)

            # Retrieve Stripe session
            session = stripe.checkout.Session.retrieve(session_id)

            # Validate session matches order
            if session.metadata.get('order_oid') != order_oid:
                return Response(
                    {"message": "Session does not match order"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Handle payment status
            if session.payment_status == "paid":
                return self._handle_successful_payment(order, session)
            else:
                return Response(
                    {"message": f"Payment status: {session.payment_status}"},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )

        except CartOrder.DoesNotExist:
            return Response(
                {"message": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            return Response(
                {"error": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _handle_successful_payment(self, order, session):
        """Handle all post-payment success logic"""
        if order.payment_status != "paid":
            # Update order status
            order.payment_status = "paid"
            # Note: paid_at field doesn't exist in model, using date field instead
            order.save()

            # Process notifications
            self._process_notifications(order)

            return Response({"message": "Payment successful"})
        
        return Response({"message": "Order already paid"})

    def _process_notifications(self, order):
        """Send all post-payment notifications"""
        if order.buyer:
            # Buyer notification
            send_notification(user=order.buyer, order=order)
            self._send_email(
                user=order.buyer,
                order=order,
                subject="Order Placed Successfully",
                templates=(
                    "email/customer_order_confirmation.txt",
                    "email/customer_order_confirmation.html"
                )
            )

        # Vendor notifications
        for item in order.orderitem.all():
            if item.vendor:
                send_notification(vendor=item.vendor, order=order, order_item=item)
                self._send_email(
                    user=item.vendor.user,
                    order=order,
                    order_item=item,
                    subject="New Sale!",
                    templates=(
                        "email/vendor_sale.txt",
                        "email/vendor_sale.html"
                    )
                )

    def _send_email(self, user, order, order_item=None, subject="", templates=()):
        """Helper method to send templated emails"""
        context = {
            'order': order,
            'order_item': order_item,
            'user': user
        }
        
        text_body = render_to_string(templates[0], context)
        html_body = render_to_string(templates[1], context)

        msg = EmailMultiAlternatives(
            subject=subject,
            from_email=settings.FROM_EMAIL,
            to=[user.email],
            body=text_body
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()

class ReviewListAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return Review.objects.filter(product_id=product_id, active=True)

class ReviewRatingAPIView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data
        Review.objects.create(
            user_id=payload['user_id'],
            product_id=payload['product_id'],
            rating=payload['rating'],
            review=payload['review']
        )
        return Response({"message": "Review Created Successfully."}, status=status.HTTP_201_CREATED)

class SearchProductAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        query = self.request.GET.get('query')
        return Product.objects.filter(status="published", title__icontains=query)

class CarouselImageList(generics.ListAPIView):
    queryset = CarouselImage.objects.filter(is_active=True)
    serializer_class = CarouselImageSerializer
    permission_classes = [AllowAny]

class OffersCarouselList(generics.ListAPIView):
    queryset = OffersCarousel.objects.filter(is_active=True)
    serializer_class = OffersCarouselSerializer
    permission_classes = [AllowAny]

class BannerListAPIView(generics.ListAPIView):
    queryset = Banner.objects.filter(is_active=True)
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]

class MostViewedProductsAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.filter(status="published").order_by('-views')[:18]


class MostBoughtProductsAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # For now, return featured products or products with highest views
        # This avoids complex database annotations that might cause issues
        try:
            # First try to get featured products
            featured_products = Product.objects.filter(
                status="published",
                featured=True
            )[:18]
            
            if featured_products.exists():
                print(f"Returning {featured_products.count()} featured products")
                return featured_products
            
            # If no featured products, return products with highest views
            print("No featured products, returning products with highest views")
            return Product.objects.filter(status="published").order_by('-views')[:18]
            
        except Exception as e:
            print(f"Error in MostBoughtProductsAPIView: {e}")
            # Ultimate fallback: just return published products
            return Product.objects.filter(status="published")[:18]

# Live Orders Feed for Admin Dashboard
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.db.models import Count, Sum, Avg
from datetime import datetime, timedelta
from django.utils import timezone

@method_decorator(staff_member_required, name='dispatch')
class LiveOrdersFeedView(generics.ListAPIView):
    """Live orders feed for admin dashboard - shows recent orders with real-time updates"""
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Get recent orders (last 24 hours) ordered by most recent
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=24)
        return CartOrder.objects.filter(
            date__gte=cutoff_time
        ).order_by('-date')[:50]  # Limit to 50 most recent orders
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Add additional context for live feed
        context = {
            'orders': serializer.data,
            'total_orders': queryset.count(),
            'whatsapp_orders': queryset.filter(payment_method='whatsapp').count(),
            'pending_orders': queryset.filter(payment_status='pending').count(),
            'confirmed_orders': queryset.filter(payment_status='confirmed').count(),
            'paid_orders': queryset.filter(payment_status='paid').count(),
            'last_updated': timezone.now().isoformat(),
        }
        
        return Response(context)

@staff_member_required
def live_orders_feed(request):
    """Simple view for live orders feed - returns JSON for AJAX updates"""
    try:
        # Get time period filter
        time_period = request.GET.get('time_period', 'day')
        
        # Determine cutoff time based on period
        now = timezone.now()
        if time_period == 'week':
            cutoff_time = now - timedelta(days=7)
        elif time_period == 'month':
            cutoff_time = now - timedelta(days=30)
        else:  # default to day
            cutoff_time = now - timedelta(hours=24)
        
        # Get recent orders with error handling
        try:
            recent_orders = CartOrder.objects.filter(
                date__gte=cutoff_time
            ).order_by('-date')[:50]
        except Exception as db_error:
            return JsonResponse({
                'success': False,
                'error': f'Database query error: {str(db_error)}'
            }, status=500)
        
        orders_data = []
        for order in recent_orders:
            try:
                # Handle potential None values safely
                buyer_name = order.full_name or 'Unknown'
                total = float(order.total) if order.total else 0.0
                payment_status = order.payment_status or 'pending'
                order_status = order.order_status or 'pending'
                payment_method = order.payment_method or 'unknown'
                date_str = order.date.isoformat() if order.date else timezone.now().isoformat()
                
                orders_data.append({
                    'id': order.id,
                    'oid': str(order.oid),
                    'buyer_name': buyer_name,
                    'total': total,
                    'payment_status': payment_status,
                    'order_status': order_status,
                    'payment_method': payment_method,
                    'date': date_str,
                    'is_whatsapp': payment_method == 'whatsapp',
                    'status_color': {
                        'pending': '#ffc107',
                        'confirmed': '#17a2b8', 
                        'paid': '#28a745',
                        'cancelled': '#dc3545',
                        'expired': '#6c757d'
                    }.get(payment_status, '#6c757d')
                })
            except Exception as order_error:
                # Log the problematic order but continue with others
                print(f"Error processing order {order.id}: {str(order_error)}")
                continue
        
        context = {
            'success': True,
            'orders': orders_data,
            'total_orders': len(orders_data),
            'whatsapp_orders': len([o for o in orders_data if o.get('is_whatsapp', False)]),
            'last_updated': timezone.now().isoformat(),
        }
        
        return JsonResponse(context)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'details': error_details
        }, status=500)

@staff_member_required
def dashboard_stats(request):
    """
    AJAX endpoint for dashboard statistics with filtering
    """
    try:
        # Get filter parameters
        time_period = request.GET.get('time_period', 'week')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Determine date range based on filter
        now = timezone.now()
        
        if time_period == 'today':
            start_date = now - timedelta(hours=24)
            end_date = now
        elif time_period == 'yesterday':
            start_date = now - timedelta(hours=48)
            end_date = now - timedelta(hours=24)
        elif time_period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif time_period == 'month':
            start_date = now - timedelta(days=30)
            end_date = now
        elif time_period == 'custom' and start_date and end_date:
            try:
                start_date = timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                end_date = timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
            except ValueError:
                start_date = now - timedelta(days=7)
                end_date = now
        else:
            start_date = now - timedelta(days=7)
            end_date = now
        
        # Get filtered orders with error handling
        try:
            filtered_orders = CartOrder.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            )
        except Exception as e:
            print(f"Error filtering orders: {e}")
            filtered_orders = CartOrder.objects.none()
        
        # Apply additional filters if provided
        payment_status = request.GET.get('payment_status')
        if payment_status and payment_status != 'all':
            filtered_orders = filtered_orders.filter(payment_status=payment_status)
            
        order_status = request.GET.get('order_status')
        if order_status and order_status != 'all':
            filtered_orders = filtered_orders.filter(order_status=order_status)
            
        payment_method = request.GET.get('payment_method')
        if payment_method and payment_method != 'all':
            filtered_orders = filtered_orders.filter(payment_method=payment_method)
        
        # Calculate comprehensive stats with error handling
        try:
            total_orders = filtered_orders.count()
            total_sales = sum(order.total for order in filtered_orders)
            avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        except Exception as e:
            print(f"Error calculating basic stats: {e}")
            total_orders = 0
            total_sales = 0
            avg_order_value = 0
        
        # Payment method breakdown with error handling
        try:
            payment_methods = filtered_orders.values('payment_method').annotate(
                count=Count('id'),
                total=Sum('total')
            )
        except Exception as e:
            print(f"Error calculating payment methods: {e}")
            payment_methods = []
        
        # Payment status breakdown with error handling
        try:
            payment_statuses = filtered_orders.values('payment_status').annotate(
                count=Count('id'),
                total=Sum('total')
            )
        except Exception as e:
            print(f"Error calculating payment statuses: {e}")
            payment_statuses = []
        
        # Order status breakdown with error handling
        try:
            order_statuses = filtered_orders.values('order_status').annotate(
                count=Count('id'),
                total=Sum('total')
            )
        except Exception as e:
            print(f"Error calculating order statuses: {e}")
            order_statuses = []
        
        # Daily breakdown for charts with error handling
        try:
            daily_breakdown = filtered_orders.extra(
                select={'day': 'date(date)'}
            ).values('day').annotate(
                orders=Count('id'),
                sales=Sum('total')
            ).order_by('day')
        except Exception as e:
            print(f"Error calculating daily breakdown: {e}")
            daily_breakdown = []
        
        # Performance metrics with error handling
        try:
            whatsapp_orders = filtered_orders.filter(payment_method='whatsapp').count()
        except Exception as e:
            print(f"Error counting WhatsApp orders: {e}")
            whatsapp_orders = 0
        
        # Calculate realistic metrics based on available data
        
        # New customers this period (unique emails not seen before)
        try:
            previous_start = start_date - (end_date - start_date)
            previous_customers = set(CartOrder.objects.filter(
                date__gte=previous_start,
                date__lt=start_date
            ).values_list('email', flat=True))
            
            # Get actual registered users count instead of order emails
            from userauths.models import User
            total_unique_customers = User.objects.count()
            
            # For new customers calculation, still use order emails
            current_customers = set(filtered_orders.values_list('email', flat=True))
            previous_customers = set(CartOrder.objects.filter(
                date__gte=previous_start,
                date__lt=start_date
            ).values_list('email', flat=True))
            new_customers = len(current_customers - previous_customers)
            
            # Calculate new customer percentage
            new_customer_rate = (new_customers / max(1, total_unique_customers)) * 100 if total_unique_customers > 0 else 0
            
            # Average order value trend (compare current period with previous)
            current_avg = filtered_orders.aggregate(avg=Avg('total'))['avg'] or 0
            previous_orders = CartOrder.objects.filter(
                date__gte=previous_start,
                date__lt=start_date
            )
            previous_avg = previous_orders.aggregate(avg=Avg('total'))['avg'] or 0
            
            # Calculate percentage change in average order value
            if previous_avg > 0:
                avg_order_change = ((current_avg - previous_avg) / previous_avg) * 100
            else:
                avg_order_change = 0.0
            
            # Order frequency (how many orders per customer on average)
            if total_unique_customers > 0:
                orders_per_customer = total_orders / total_unique_customers
            else:
                orders_per_customer = 0.0
                
        except Exception as e:
            print(f"Error calculating performance metrics: {e}")
            new_customer_rate = 0
            avg_order_change = 0
            orders_per_customer = 0
        
        stats = {
            'summary': {
                'total_orders': total_orders,
                'total_sales': float(total_sales),
                'avg_order_value': float(avg_order_value),
                'whatsapp_orders': whatsapp_orders,
            },
            'breakdowns': {
                'payment_methods': list(payment_methods),
                'payment_statuses': list(payment_statuses),
                'order_statuses': list(order_statuses),
            },
            'daily_data': list(daily_breakdown),
            'performance': {
                'total_users': total_unique_customers,
                'avg_order_change': round(avg_order_change, 1),
                'orders_per_customer': round(orders_per_customer, 1),
            },
            'filters': {
                'time_period': time_period,
                'start_date': start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                'end_date': end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                'payment_status': payment_status,
                'order_status': order_status,
                'payment_method': payment_method,
            },
            # Add the fields that the frontend JavaScript expects
            'filtered_sales': float(total_sales),
            'today_sales': float(total_sales) if time_period == 'today' else 0,
            'total_orders_count': total_orders,
            'whatsapp_orders_count': whatsapp_orders
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in dashboard_stats: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def performance_metrics(request):
    """
    AJAX endpoint for real-time performance metrics
    """
    try:
        now = timezone.now()
        
        # Get real-time metrics with error handling
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            today_orders = CartOrder.objects.filter(date__gte=today_start).count()
            today_sales = sum(order.total for order in CartOrder.objects.filter(date__gte=today_start))
        except Exception as e:
            print(f"Error calculating today metrics: {e}")
            today_orders = 0
            today_sales = 0
        
        # Calculate hourly trends with error handling
        hourly_orders = []
        try:
            for hour in range(24):
                hour_start = today_start.replace(hour=hour)
                hour_end = hour_start + timedelta(hours=1)
                hour_orders = CartOrder.objects.filter(
                    date__gte=hour_start,
                    date__lt=hour_end
                ).count()
                hourly_orders.append({
                    'hour': hour,
                    'orders': hour_orders
                })
        except Exception as e:
            print(f"Error calculating hourly trends: {e}")
            hourly_orders = []
        
        # Get top performing products with error handling
        try:
            top_products = CartOrderItem.objects.filter(
                order__date__gte=today_start
            ).values('product__title').annotate(
                total_quantity=Sum('qty'),
                total_revenue=Sum('total')
            ).order_by('-total_revenue')[:5]
        except Exception as e:
            print(f"Error getting top products: {e}")
            top_products = []
        
        # Get recent activity with error handling
        try:
            recent_activity = CartOrder.objects.filter(
                date__gte=now - timedelta(hours=6)
            ).order_by('-date')[:10]
        except Exception as e:
            print(f"Error getting recent activity: {e}")
            recent_activity = []
        
        activity_data = []
        for order in recent_activity:
            try:
                activity_data.append({
                    'id': order.id,
                    'oid': order.oid,
                    'customer': order.full_name or (order.buyer.username if order.buyer else 'Guest'),
                    'amount': float(order.total),
                    'status': order.payment_status,
                    'method': order.payment_method,
                    'time_ago': order.date.strftime('%H:%M'),
                    'type': 'order'
                })
            except Exception as e:
                print(f"Error processing activity item {order.id}: {e}")
                continue
        
        # Calculate realistic performance metrics based on available data
        
        # New customers this period (unique emails not seen before)
        period_start = today_start
        previous_period_start = period_start - timedelta(days=7)  # 7 days before current period
        
        try:
            # Get all customers from previous period
            previous_customers = set(CartOrder.objects.filter(
                date__gte=previous_period_start,
                date__lt=period_start
            ).values_list('email', flat=True))
            
            # Get actual registered users count instead of order emails
            from userauths.models import User
            total_unique_customers = User.objects.count()
            
            # For new customers calculation, still use order emails
            current_customers = set(CartOrder.objects.filter(
                date__gte=period_start
            ).values_list('email', flat=True))
            
            # New customers = current customers not in previous period
            new_customers = len(current_customers - previous_customers)
            
            # Calculate new customer percentage
            new_customer_rate = (new_customers / max(1, total_unique_customers)) * 100 if total_unique_customers > 0 else 0
            
            # Average order value trend (compare current period with previous)
            current_orders = CartOrder.objects.filter(date__gte=period_start)
            current_avg = current_orders.aggregate(avg=Avg('total'))['avg'] or 0
            previous_orders = CartOrder.objects.filter(
                date__gte=previous_period_start,
                date__lt=period_start
            )
            previous_avg = previous_orders.aggregate(avg=Avg('total'))['avg'] or 0
            
            # Calculate percentage change in average order value
            if previous_avg > 0:
                avg_order_change = ((current_avg - previous_avg) / previous_avg) * 100
            else:
                avg_order_change = 0.0
            
            # Order frequency (how many orders per customer on average)
            if total_unique_customers > 0:
                orders_per_customer = today_orders / total_unique_customers
            else:
                orders_per_customer = 0.0
                
        except Exception as e:
            print(f"Error calculating performance metrics: {e}")
            new_customer_rate = 0
            avg_order_change = 0
            orders_per_customer = 0
        
        metrics = {
            'today_summary': {
                'orders': today_orders,
                'sales': float(today_sales),
                'avg_order': float(today_sales / today_orders) if today_orders > 0 else 0
            },
            'performance': {
                'total_users': total_unique_customers,
                'avg_order_change': round(avg_order_change, 1),
                'orders_per_customer': round(orders_per_customer, 1),
            },
            'hourly_trends': hourly_orders,
            'top_products': list(top_products),
            'recent_activity': activity_data,
            'last_updated': now.isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        print(f"Error in performance_metrics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(['POST'])
def whatsapp_checkout(request):
    """
    Create a CartOrder for WhatsApp checkout
    """
    print("=" * 50)
    print("WHATSAPP CHECKOUT FUNCTION CALLED")
    print("=" * 50)
    try:
        print(f"WhatsApp checkout request received: {request.body}")
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
            print(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Invalid JSON: {str(e)}'
            }, status=400)
        
        cart_items = data.get('cart_items', [])
        customer_info = data.get('customer_info', {})
        
        print(f"Cart items: {cart_items}")
        print(f"Customer info: {customer_info}")
        
        # Basic validation
        if not cart_items:
            return JsonResponse({
                'success': False,
                'error': 'No cart items provided'
            }, status=400)
        
        if not customer_info.get('full_name') or not customer_info.get('email'):
            return JsonResponse({
                'success': False,
                'error': 'Full name and email are required'
            }, status=400)
        
        # Calculate totals
        sub_total = Decimal('0.00')
        shipping_amount = Decimal('0.00')
        tax_fee = Decimal('0.00')
        service_fee = Decimal('0.00')
        
        print("Creating order...")
        
        with transaction.atomic():
            # Create the order first
            order = CartOrder.objects.create(
                payment_method='whatsapp',
                payment_status='pending',
                order_status='pending',
                sub_total=sub_total,
                shipping_ammount=shipping_amount,
                tax_fee=tax_fee,
                service_fee=service_fee,
                total=sub_total,
                full_name=customer_info.get('full_name', ''),
                email=customer_info.get('email', ''),
                phone=customer_info.get('phone', ''),
                address=customer_info.get('address', ''),
                city=customer_info.get('city', ''),
                state=customer_info.get('state', ''),
                country=customer_info.get('country', ''),
                buyer=None,
            )
            
            print(f"Order created: {order.oid}")
            
            # Create order items
            for item in cart_items:
                try:
                    product = Product.objects.get(id=item['product_id'])
                    price = Decimal(str(item['price']))
                    qty = int(item['qty'])
                    item_subtotal = price * qty
                    sub_total += item_subtotal
                    
                    CartOrderItem.objects.create(
                        order=order,
                        product=product,
                        qty=qty,
                        color=item.get('color'),
                        size=item.get('size'),
                        price=price,
                        sub_total=item_subtotal,
                        total=item_subtotal,
                        vendor=product.vendor
                    )
                    
                    print(f"Created order item for {product.title}")
                    
                except Exception as e:
                    print(f"Error creating order item: {e}")
                    raise e
            
            # Update order totals
            order.sub_total = sub_total
            order.total = sub_total + shipping_amount + tax_fee + service_fee
            order.save()
            
            print(f"Order {order.oid} completed with total: ${order.total}")
        
        print(f"SUCCESS: Order {order.oid} created successfully!")
        print("=" * 50)
        return JsonResponse({
            'success': True,
            'order_id': order.oid,
            'message': 'WhatsApp order created successfully'
        })
        
    except Exception as e:
        print(f"Error in WhatsApp checkout: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

from django.views.decorators.http import require_http_methods
import os

@require_http_methods(['GET', 'OPTIONS'])
def serve_media_file(request, file_path):
    """Simple media file serving view with CORS support"""
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    try:
        media_root = settings.MEDIA_ROOT
        full_path = os.path.join(media_root, file_path)
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            response = FileResponse(open(full_path, 'rb'))
            
            # Add CORS headers to allow cross-origin requests
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"
            
            # Set proper content type for images
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                response["Content-Type"] = "image/" + file_path.split('.')[-1].lower()
            
            return response
        else:
            raise Http404(f"File not found: {file_path}")
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")

def test_media(request):
    """Test view to debug media file serving"""
    from django.http import HttpResponse
    import os
    
    # Check if media files exist
    media_root = settings.MEDIA_ROOT
    products_dir = os.path.join(media_root, 'products')
    
    if os.path.exists(products_dir):
        files = os.listdir(products_dir)
        return HttpResponse(f"Media files found: {files[:10]}")  # Show first 10 files
    else:
        return HttpResponse("Products directory not found")
    
    return HttpResponse("Test view working")

# Simple health check that doesn't depend on external packages
def simple_health_check(request):
    """
    Simple health check endpoint for Railway monitoring
    Returns 200 OK if the application is running
    """
    from django.http import HttpResponse
    from django.utils import timezone
    
    return HttpResponse(
        f"SuperParaguai E-commerce API is running - {timezone.now().isoformat()}",
        status=200
    )

@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint for Railway monitoring
    Returns 200 OK if the application is running
    """
    return Response(
        {
            'status': 'healthy',
            'message': 'SuperParaguai E-commerce API is running',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0'
        },
        status=status.HTTP_200_OK
    )