from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
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

            product = Product.objects.get(status="published", id=product_id)
            
            # Check product stock
            if product.stock_qty < qty:
                return Response(
                    {"error": f"Not enough stock for {product.title}. Available: {product.stock_qty}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check color stock if specified
            if color and color != "No Color":
                color_obj = Color.objects.filter(product=product, name=color).first()
                if not color_obj or color_obj.stock_qty < qty:
                    return Response(
                        {"error": f"Selected color {color} is out of stock"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check size stock if specified
            if size and size != "No Size":
                size_obj = Size.objects.filter(product=product, name=size).first()
                if not size_obj or size_obj.stock_qty < qty:
                    return Response(
                        {"error": f"Selected size {size} is out of stock"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            user = User.objects.get(id=user_id) if user_id and user_id != 'undefined' else None
            tax = Tax.objects.filter(country=country).first()
            tax_rate = tax.rate / 100 if tax else 0

            sub_total = price * qty
            shipping_total = shipping_ammount * qty
            tax_fee = sub_total * Decimal(tax_rate)
            service_fee = sub_total * Decimal(0.01)
            total = sub_total + shipping_total + tax_fee + service_fee

            cart = Cart.objects.filter(cart_id=cart_id, product=product, color=color, size=size).first()
            if not cart:
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
                {'message': "Cart Updated Successfully" if cart.id else "Cart Created Successfully"},
                status=status.HTTP_200_OK if cart.id else status.HTTP_201_CREATED
            )

        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
        item_id = self.kwargs['item_id']
        return Cart.objects.get(id=item_id)

    def perform_destroy(self, instance):
        instance.product.stock_qty += instance.qty
        instance.product.save()
        instance.delete()

class createOrderAPIView(generics.CreateAPIView):
    serializer_class = CartOrderSerializer
    queryset = CartOrder.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        payload = request.data
        with transaction.atomic():
            try:
                # Create order
                order = CartOrder.objects.create(
                    buyer=User.objects.get(id=payload['user_id']) if payload['user_id'] != 0 else None,
                    payment_status="pending",
                    full_name=payload['full_name'],
                    email=payload['email'],
                    phone=payload['phone'],
                    address=payload['address'],
                    city=payload['city'],
                    state=payload['state'],
                    country=payload['country']
                )

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

                    # Update product stock
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
                    {"message": "Order Created Successfully", "order_oid": order.oid},
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

class CheckoutView(generics.RetrieveAPIView):
    serializer_class = CartOrderSerializer
    lookup_field = 'order_oid'
    permission_classes = [AllowAny]

    def get_object(self):
        order_oid = self.kwargs['order_oid']
        return CartOrder.objects.get(oid=order_oid)

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
            order = CartOrder.objects.select_related('buyer').get(oid=order_oid)
            
            # Early return if already paid
            if order.payment_status == 'paid':
                return Response(
                    {"message": "Order already paid"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create line items from order items
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.title,
                    },
                    'unit_amount': int(item.price * 100),  # Convert to cents
                },
                'quantity': item.qty,
            } for item in order.orderitem.all()]

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

            # Update order with session info
            order.stripe_session_id = checkout_session.id
            order.save(update_fields=['stripe_session_id'])

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
            return Response(
                {"error": f"Server error: {str(e)}"},
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
            order.paid_at = timezone.now()
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
                send_notification(user=item.vendor, order=order, order_item=item)
                self._send_email(
                    user=item.vendor,
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