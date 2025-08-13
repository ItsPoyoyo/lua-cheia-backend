from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

# Create your views here.

from userauths.models import User
from store.models import Coupon, Wishlist, Product, Tax, Category,Review, Cart, Size, Color, CartOrder, CartOrderItem, Notification
from store.serializers import CartSerializer, WishlistSerializer, ReviewSerializer, CategorySerializer,CartOrderItem,CartOrderItemSerializer,CartOrder, ProductSerializer, CategorySerializer, CartOrderSerializer, CouponSerializer, NotificationSerializer

from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound

from decimal import Decimal

from userauths.models import Profile, User 
from userauths.serializer import ProfileSerializer

import stripe


class OrderAPIView(generics.ListAPIView):
    serializer_class = CartOrderSerializer 
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        try:
            user = User.objects.get(id=user_id)
            # Show all orders for the user, not just paid ones
            orders = CartOrder.objects.filter(buyer=user).order_by('-date')
            return orders
        except User.DoesNotExist:
            return CartOrder.objects.none()
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return CartOrder.objects.none()

class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CartOrderSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated if needed

    def get_object(self):
        # Retrieve the `user_id` and `order_oid` from the URL kwargs
        user_id = self.kwargs['user_id']
        order_oid = self.kwargs['order_oid']

        try:
            # Look up the user
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found")

        try:
            # Look up the order using both user_id and order_oid, regardless of payment status
            order = CartOrder.objects.get(oid=order_oid, buyer=user)
        except CartOrder.DoesNotExist:
            raise NotFound("Order not found")

        return order


    
class WishlistAPIView(generics.ListCreateAPIView):
    serializer_class = WishlistSerializer
    permission_classes = (AllowAny, )

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        wishlists = Wishlist.objects.filter(user=user)
        return wishlists

    def create(self, request, *args, **kwargs):
        payload = self.request.data
        product_id = payload['product_id']
        user_id = payload['user_id']

        product = Product.objects.get(id=product_id)
        user = User.objects.get(id=user_id)

        # Check if product is already in the wishlist for this user
        existing_wishlist = Wishlist.objects.filter(product=product, user=user).first()

        if existing_wishlist:
            existing_wishlist.delete()
            return Response({"message": "Removed From Wishlist"}, status=status.HTTP_200_OK)
        else:
            # Initialize the serializer properly
            serializer = self.get_serializer(data={"product": product.id, "user": user.id})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Added To Wishlist"}, status=status.HTTP_201_CREATED)


class CustomerNotificationAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (AllowAny, )

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        notifications = Notification.objects.filter(user=user, seen=False)
        return notifications

class MarkCustomerNotificationAsSeenAPIView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (AllowAny, )

    def get_object(self):
        user_id = self.kwargs['user_id']
        notification_id = self.kwargs['notification_id']

        user = User.objects.get(id=user_id)
        notification = Notification.objects.get(id=notification_id, user=user)

        if notification != True:
            notification.seen = True
            notification.save()

        return notification

class CustomerUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = (AllowAny, )