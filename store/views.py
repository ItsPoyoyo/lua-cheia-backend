from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

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

def validate_product_stock(product, quantity, color_name=None, size_name=None):
    """
    Improved stock validation with better error handling
    Returns (is_valid, error_message, available_stock)
    """
    try:
        # Check if product exists and is published
        if product.status != "published":
            return False, f"{product.title} is not available for purchase", 0
        
        # Check if product is marked as in stock
        if not product.in_stock:
            return False, f"{product.title} is currently out of stock", 0
        
        # Start with main product stock
        available_stock = product.stock_qty
        
        # Normalize color and size values
        color_name = color_name.strip() if color_name else None
        size_name = size_name.strip() if size_name else None
        
        # Handle empty strings and None values
        if color_name in [None, '', 'null', 'undefined', 'No Color']:
            color_name = None
        if size_name in [None, '', 'null', 'undefined', 'No Size']:
            size_name = None
        
        # Check color stock if specified
        if color_name:
            try:
                color = product.colors.get(name__iexact=color_name)  # Case insensitive
                if not color.in_stock or color.stock_qty <= 0:
                    return False, f"Color '{color_name}' is out of stock for {product.title}", 0
                # Use the minimum of product stock and color stock
                available_stock = min(available_stock, color.stock_qty)
            except Color.DoesNotExist:
                return False, f"Color '{color_name}' is not available for {product.title}", 0
        
        # Check size stock if specified
        if size_name:
            try:
                size = product.sizes.get(name__iexact=size_name)  # Case insensitive
                if not size.in_stock or size.stock_qty <= 0:
                    return False, f"Size '{size_name}' is out of stock for {product.title}", 0
                # Use the minimum of current available stock and size stock
                available_stock = min(available_stock, size.stock_qty)
            except Size.DoesNotExist:
                return False, f"Size '{size_name}' is not available for {product.title}", 0
        
        # Check if requested quantity is available
        if available_stock < quantity:
            if available_stock == 0:
                variant_info = ""
                if color_name:
                    variant_info += f" in {color_name}"
                if size_name:
                    variant_info += f" size {size_name}"
                return False, f"{product.title}{variant_info} is out of stock", 0
            else:
                variant_info = ""
                if color_name:
                    variant_info += f" in {color_name}"
                if size_name:
                    variant_info += f" size {size_name}"
                return False, f"Only {available_stock} available{variant_info} for {product.title}", available_stock
        
        # Check cart limit
        if quantity > product.max_cart_limit:
            return False, f"Maximum {product.max_cart_limit} items allowed per order for {product.title}", available_stock
        
        return True, "Stock available", available_stock
        
    except Exception as e:
        print(f"Stock validation error: {str(e)}")  # For debugging
        return False, f"Error validating stock. Please try again.", 0

def update_product_stock(product, quantity, color_name=None, size_name=None):
    """
    Update stock levels after successful order with better error handling
    """
    try:
        # Normalize color and size values
        color_name = color_name.strip() if color_name else None
        size_name = size_name.strip() if size_name else None
        
        # Handle empty strings and None values
        if color_name in [None, '', 'null', 'undefined', 'No Color']:
            color_name = None
        if size_name in [None, '', 'null', 'undefined', 'No Size']:
            size_name = None
        
        # Update main product stock
        if product.stock_qty >= quantity:
            product.stock_qty -= quantity
            if product.stock_qty <= 0:
                product.in_stock = False
            product.save()
        else:
            raise Exception(f"Insufficient product stock for {product.title}")
        
        # Update color stock if specified
        if color_name:
            try:
                color = product.colors.get(name__iexact=color_name)
                if color.stock_qty >= quantity:
                    color.stock_qty -= quantity
                    if color.stock_qty <= 0:
                        color.in_stock = False
                    color.save()
                else:
                    raise Exception(f"Insufficient color stock for {color_name}")
            except Color.DoesNotExist:
                pass  # Color was deleted during order processing
        
        # Update size stock if specified
        if size_name:
            try:
                size = product.sizes.get(name__iexact=size_name)
                if size.stock_qty >= quantity:
                    size.stock_qty -= quantity
                    if size.stock_qty <= 0:
                        size.in_stock = False
                    size.save()
                else:
                    raise Exception(f"Insufficient size stock for {size_name}")
            except Size.DoesNotExist:
                pass  # Size was deleted during order processing
                
    except Exception as e:
        raise Exception(f"Error updating stock for {product.title}: {str(e)}")

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
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        slug = self.kwargs['slug']
        product = Product.objects.get(slug=slug)
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
            product_id = payload['product_id']
            user_id = payload.get('user_id')
            qty = int(payload.get('qty', 1))
            price = Decimal(payload.get('price', 0))
            shipping_ammount = Decimal(payload.get('shipping_ammount', 0))
            country = payload.get('country')
            size = payload.get('size')
            color = payload.get('color')
            cart_id = payload.get('cart_id')

            # Validate quantity
            if qty <= 0:
                return Response(
                    {"error": "Quantity must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            product = Product.objects.get(status="published", id=product_id)
            
            # Use improved stock validation
            is_valid, error_msg, available_stock = validate_product_stock(
                product, qty, color, size
            )
            
            if not is_valid:
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(id=user_id) if user_id and user_id != 'undefined' else None
            tax = Tax.objects.filter(country=country, active=True).first()
            tax_rate = tax.rate / 100 if tax else 0

            sub_total = price * qty
            shipping_total = shipping_ammount * qty
            tax_fee = sub_total * Decimal(tax_rate)
            service_fee = sub_total * Decimal(0.01)
            total = sub_total + shipping_total + tax_fee + service_fee

            # Check if item already exists in cart
            cart = Cart.objects.filter(
                cart_id=cart_id, 
                product=product, 
                color=color or "No Color", 
                size=size or "No Size"
            ).first()
            
            if cart:
                # Update existing cart item
                new_qty = cart.qty + qty
                
                # Re-validate stock for new quantity using improved validation
                is_valid_update, error_msg_update, available_stock_update = validate_product_stock(
                    product, new_qty, color, size
                )
                
                if not is_valid_update:
                    remaining = max(0, available_stock - cart.qty)
                    if remaining == 0:
                        return Response(
                            {"error": f"Cannot add more. {product.title} is already at maximum available quantity in your cart"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    else:
                        return Response(
                            {"error": f"Cannot add {qty} more. Only {remaining} more available for {product.title}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                cart.qty = new_qty
                cart.sub_total = price * new_qty
                cart.shipping_ammount = shipping_ammount * new_qty
                cart.tax_fee = cart.sub_total * Decimal(tax_rate)
                cart.service_fee = cart.sub_total * Decimal(0.01)
                cart.total = cart.sub_total + cart.shipping_ammount + cart.tax_fee + cart.service_fee
                cart.save()
                
                return Response(
                    {'message': f"Cart updated successfully. {product.title} quantity is now {new_qty}"},
                    status=status.HTTP_200_OK
                )
            else:
                # Create new cart item
                cart = Cart.objects.create(
                    product=product,
                    user=user,
                    qty=qty,
                    price=price,
                    sub_total=sub_total,
                    shipping_ammount=shipping_total,
                    tax_fee=tax_fee,
                    color=color or "No Color",
                    size=size or "No Size",
                    country=country,
                    cart_id=cart_id,
                    service_fee=service_fee,
                    total=total
                )

                return Response(
                    {'message': f"{product.title} added to cart successfully"},
                    status=status.HTTP_201_CREATED
                )

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found or is not available"},
                status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": f"Invalid data provided: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, *args, **kwargs):
        """Update cart item quantity"""
        try:
            payload = request.data
            cart_id = payload.get('cart_id')
            product_id = payload.get('product_id')
            new_qty = int(payload.get('qty', 1))
            color = payload.get('color', 'No Color')
            size = payload.get('size', 'No Size')
            country = payload.get('country')

            # Validate quantity
            if new_qty <= 0:
                return Response(
                    {"error": "Quantity must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find the cart item
            cart_item = Cart.objects.filter(
                cart_id=cart_id,
                product_id=product_id,
                color=color,
                size=size
            ).first()

            if not cart_item:
                return Response(
                    {"error": "Cart item not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            product = cart_item.product

            # Validate stock for new quantity
            is_valid, error_msg, available_stock = validate_product_stock(
                product, new_qty, color if color != 'No Color' else None, size if size != 'No Size' else None
            )

            if not is_valid:
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update cart item
            tax = Tax.objects.filter(country=country, active=True).first()
            tax_rate = tax.rate / 100 if tax else 0

            cart_item.qty = new_qty
            cart_item.sub_total = cart_item.price * new_qty
            cart_item.shipping_ammount = cart_item.shipping_ammount / cart_item.qty * new_qty if cart_item.qty > 0 else 0
            cart_item.tax_fee = cart_item.sub_total * Decimal(tax_rate)
            cart_item.service_fee = cart_item.sub_total * Decimal(0.01)
            cart_item.total = cart_item.sub_total + cart_item.shipping_ammount + cart_item.tax_fee + cart_item.service_fee
            cart_item.save()

            return Response(
                {'message': f"Cart updated successfully. {product.title} quantity is now {new_qty}"},
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            return Response(
                {"error": f"Invalid quantity provided: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Add a dedicated cart update endpoint
class CartUpdateAPIView(generics.UpdateAPIView):
    """Dedicated endpoint for updating cart item quantities"""
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        cart_id = self.kwargs.get('cart_id')
        item_id = self.kwargs.get('item_id')
        return Cart.objects.get(cart_id=cart_id, id=item_id)
    
    def patch(self, request, *args, **kwargs):
        try:
            cart_item = self.get_object()
            new_qty = int(request.data.get('qty', 1))
            
            if new_qty <= 0:
                return Response(
                    {"error": "Quantity must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate stock
            is_valid, error_msg, available_stock = validate_product_stock(
                cart_item.product, 
                new_qty, 
                cart_item.color if cart_item.color != 'No Color' else None,
                cart_item.size if cart_item.size != 'No Size' else None
            )
            
            if not is_valid:
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update cart item
            tax = Tax.objects.filter(country=cart_item.country, active=True).first()
            tax_rate = tax.rate / 100 if tax else 0
            
            cart_item.qty = new_qty
            cart_item.sub_total = cart_item.price * new_qty
            cart_item.shipping_ammount = (cart_item.shipping_ammount / cart_item.qty) * new_qty if cart_item.qty > 0 else 0
            cart_item.tax_fee = cart_item.sub_total * Decimal(tax_rate)
            cart_item.service_fee = cart_item.sub_total * Decimal(0.01)
            cart_item.total = cart_item.sub_total + cart_item.shipping_ammount + cart_item.tax_fee + cart_item.service_fee
            cart_item.save()
            
            return Response(
                {'message': f"Cart updated successfully. {cart_item.product.title} quantity is now {new_qty}"},
                status=status.HTTP_200_OK
            )
            
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": f"Invalid quantity: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CartListView(generics.ListAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        cart_id = self.kwargs['cart_id']
        user_id = self.kwargs.get('user_id')
        
        if user_id is not None:
            user = User.objects.get(id=user_id)
            return Cart.objects.filter(user=user, cart_id=cart_id)
        return Cart.objects.filter(cart_id=cart_id)

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

class CartItemDeleteAPIView(generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        cart_id = self.kwargs['cart_id']
        item_id = self.kwargs['item_id']
        user_id = self.kwargs.get('user_id')
        
        if user_id is not None:
            user = User.objects.get(id=user_id)
            return Cart.objects.get(cart_id=cart_id, id=item_id, user=user)
        return Cart.objects.get(cart_id=cart_id, id=item_id)

class createOrderAPIView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        try:
            payload = request.data
            
            # Validate required fields
            required_fields = ['full_name', 'email', 'phone', 'address', 'city', 'state', 'country', 'cart_id']
            for field in required_fields:
                if not payload.get(field):
                    return Response(
                        {"error": f"{field.replace('_', ' ').title()} is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            full_name = payload['full_name']
            email = payload['email']
            phone = payload['phone']
            address = payload['address']
            city = payload['city']
            state = payload['state']
            country = payload['country']
            cart_id = payload['cart_id']
            user_id = payload.get('user_id')

            user = User.objects.get(id=user_id) if user_id and user_id != 'undefined' else None
            cart_items = Cart.objects.filter(cart_id=cart_id)

            if not cart_items.exists():
                return Response(
                    {"error": "Cart is empty"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                # Create order
                order = CartOrder.objects.create(
                    buyer=user,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    city=city,
                    state=state,
                    country=country
                )

                totals = {
                    'shipping': Decimal(0.0),
                    'tax': Decimal(0.0),
                    'service_fee': Decimal(0.0),
                    'sub_total': Decimal(0.0),
                    'total': Decimal(0.0),
                }

                for cart_item in cart_items:
                    # Lock product for update to prevent race conditions
                    product = Product.objects.select_for_update().get(id=cart_item.product.id)
                    
                    # Use improved stock validation for order creation
                    is_valid, error_msg, available_stock = validate_product_stock(
                        product, cart_item.qty, cart_item.color, cart_item.size
                    )
                    
                    if not is_valid:
                        raise Exception(error_msg)
                    
                    # Create order item
                    CartOrderItem.objects.create(
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

                    # Use improved stock update function
                    update_product_stock(product, cart_item.qty, cart_item.color, cart_item.size)

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
                cart_items.delete()

                return Response(
                    {"message": "Order created successfully", "order_oid": order.oid},
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class CheckoutView(generics.RetrieveAPIView):
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]
    lookup_field = "oid"

    def get_object(self):
        oid = self.kwargs['oid']
        order = CartOrder.objects.get(oid=oid)
        return order

class CouponAPIView(generics.CreateAPIView):
    serializer_class = CouponSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        payload = request.data
        order_oid = payload['order_oid']
        coupon_code = payload['coupon_code']

        order = CartOrder.objects.get(oid=order_oid)
        coupon = Coupon.objects.filter(code=coupon_code, active=True).first()

        if coupon:
            order_total = order.total
            new_total = order_total - order_total * coupon.discount / 100
            order.total = new_total
            order.saved = order_total - new_total
            order.save()

            return Response(
                {"message": "Coupon Activated", "icon": "success"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"message": "Coupon Does Not Exists", "icon": "error"},
                status=status.HTTP_404_NOT_FOUND
            )

class StripeCheckoutView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        order_oid = self.request.data['order_oid']
        order = CartOrder.objects.get(oid=order_oid)

        if not order:
            return Response(
                {"message": "Order Not Found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email=order.email,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': order.full_name,
                            },
                            'unit_amount': int(order.total * 100),
                        },
                        'quantity': 1,
                    }
                ],
                mode='payment',
                success_url=settings.FRONTEND_URL + '/payment-success/' + order.oid + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=settings.FRONTEND_URL + '/payment-failed/?session_id={CHECKOUT_SESSION_ID}',
            )

            order.stripe_payment_intent = checkout_session['id']
            order.save()

            return Response({"checkout_url": checkout_session.url})

        except Exception as e:
            return Response(
                {"error": f"Something went wrong when trying to make payment. Error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentSuccessView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        payload = request.data
        order_oid = payload['order_oid']
        session_id = payload['session_id']

        order = CartOrder.objects.get(oid=order_oid)
        order_items = CartOrderItem.objects.filter(order=order)

        if session_id != 'null':
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == 'paid':
                if order.payment_status == "processing":
                    order.payment_status = "paid"
                    order.save()

                    if order.buyer != None:
                        send_notification(user=order.buyer, order=order)

                    for o in order_items:
                        send_notification(vendor=o.vendor, order=order, order_item=o)

                    context = {
                        'order': order,
                        'order_items': order_items,
                    }
                    subject = f"Order Placed Successfully"
                    text_body = render_to_string("email/customer_order_confirmation.txt", context)
                    html_body = render_to_string("email/customer_order_confirmation.html", context)

                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=text_body,
                        from_email=settings.FROM_EMAIL,
                        to=[order.email]
                    )
                    msg.attach_alternative(html_body, "text/html")
                    msg.send()

                return Response({"message": "Payment Successful"})
            else:
                return Response({"message": "Payment Failed"})
        else:
            session = None

        return Response({"message": "Payment Successful"})

class ReviewListAPIView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        product = Product.objects.get(id=product_id)
        return Review.objects.filter(product=product, active=True)

    def create(self, request, *args, **kwargs):
        payload = request.data
        user_id = payload['user_id']
        product_id = payload['product_id']
        rating = payload['rating']
        review = payload['review']

        user = User.objects.get(id=user_id)
        product = Product.objects.get(id=product_id)

        Review.objects.create(
            user=user,
            product=product,
            rating=rating,
            review=review,
        )

        return Response({"message": "Review created successfully"}, status=status.HTTP_201_CREATED)

class ReviewRatingAPIView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data
        user_id = payload['user_id']
        product_id = payload['product_id']
        rating = payload['rating']
        review = payload['review']

        user = User.objects.get(id=user_id)
        product = Product.objects.get(id=product_id)

        Review.objects.create(
            user=user,
            product=product,
            rating=rating,
            review=review,
        )

        return Response({"message": "Review created successfully"}, status=status.HTTP_201_CREATED)

class SearchProductAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        query = self.request.GET.get('query')
        return Product.objects.filter(title__icontains=query, status="published")

class CarouselImageList(generics.ListAPIView):
    serializer_class = CarouselImageSerializer
    permission_classes = [AllowAny]
    queryset = CarouselImage.objects.filter(is_active=True)

class OffersCarouselList(generics.ListAPIView):
    serializer_class = OffersCarouselSerializer
    permission_classes = [AllowAny]
    queryset = OffersCarousel.objects.filter(is_active=True)

class BannerListAPIView(generics.ListAPIView):
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]
    queryset = Banner.objects.filter(is_active=True)

class MostViewedProductsAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Product.objects.filter(status="published").order_by('-views')[:10]

# Carousel Automation API Views
from store.carousel_automation import CarouselAutomation

class CarouselAutomationAPIView(generics.GenericAPIView):
    """
    API endpoint to trigger carousel automation
    """
    
    def post(self, request):
        try:
            automation_type = request.data.get('type', 'all')
            force = request.data.get('force', False)
            
            automation = CarouselAutomation()
            
            if automation_type == 'offers':
                result = automation.update_offers_carousel(force=force)
                message = 'Offers carousel updated successfully' if result else 'Failed to update offers carousel'
            elif automation_type == 'banners':
                result = automation.update_promotional_banners(force=force)
                message = 'Promotional banners updated successfully' if result else 'Failed to update promotional banners'
            elif automation_type == 'images':
                result = automation.update_carousel_images(force=force)
                message = 'Carousel images updated successfully' if result else 'Failed to update carousel images'
            else:  # all
                result = automation.run_full_automation(force=force)
                message = 'Full carousel automation completed successfully' if result else 'Carousel automation failed'
            
            return Response({
                'success': result,
                'message': message,
                'type': automation_type,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK if result else status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CarouselAutomationStatusAPIView(generics.GenericAPIView):
    """
    API endpoint to check carousel automation status
    """
    
    def get(self, request):
        try:
            from store.models import OffersCarousel, Banner, CarouselImage
            
            # Get carousel statistics
            offers_count = OffersCarousel.objects.filter(is_active=True).count()
            banners_count = Banner.objects.filter(is_active=True).count()
            carousel_images_count = CarouselImage.objects.filter(is_active=True).count()
            
            # Get recent automated content
            recent_banners = Banner.objects.filter(
                title__startswith='Oferta Especial'
            ).order_by('-date')[:5]
            
            recent_carousels = OffersCarousel.objects.filter(
                is_active=True
            ).order_by('-id')[:5]
            
            return Response({
                'success': True,
                'statistics': {
                    'active_offers_carousels': offers_count,
                    'active_banners': banners_count,
                    'active_carousel_images': carousel_images_count
                },
                'recent_automated_banners': [
                    {
                        'id': banner.id,
                        'title': banner.title,
                        'date': banner.date.isoformat() if banner.date else None,
                        'is_active': banner.is_active
                    } for banner in recent_banners
                ],
                'recent_carousels': [
                    {
                        'id': carousel.id,
                        'title': carousel.title,
                        'products_count': carousel.products.count(),
                        'is_active': carousel.is_active
                    } for carousel in recent_carousels
                ],
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TriggerCarouselTaskAPIView(generics.GenericAPIView):
    """
    API endpoint to trigger carousel automation as background task
    """
    
    def post(self, request):
        try:
            automation_type = request.data.get('type', 'all')
            force = request.data.get('force', False)
            
            # For testing without Celery, run automation directly
            automation = CarouselAutomation()
            
            if automation_type == 'offers':
                result = automation.update_offers_carousel(force=force)
                message = 'Offers carousel automation completed'
            elif automation_type == 'banners':
                result = automation.update_promotional_banners(force=force)
                message = 'Banner automation completed'
            else:  # all
                result = automation.run_full_automation(force=force)
                message = 'Full carousel automation completed'
            
            return Response({
                'success': result,
                'message': f'{message} for type: {automation_type}',
                'type': automation_type,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

