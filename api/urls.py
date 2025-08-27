from django.urls import path

from userauths import views as userauths_views
from store import views as store_views

from customer import views as customer_views
from store.views import (
    CarouselImageList, OffersCarouselList, BannerListAPIView, MostViewedProductsAPIView, MostBoughtProductsAPIView
) 

from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('user/token/', userauths_views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', userauths_views.RegisterView.as_view()),
    path('user/password-reset/<email>/', userauths_views.PasswordResetEmailVerify.as_view(), name="password_reset"),
    path('user/password-change/', userauths_views.PasswordChangeView.as_view(), name="password_change"),
    path('user/profile/<user_id>/', userauths_views.ProfileView.as_view(), name="user_profile"),


    # Store Endpoint
    path('category/', store_views.CategoryListAPIView.as_view()),
    path('products/', store_views.ProductListAPIView.as_view()),
    path('products/<slug>/', store_views.ProductDetailAPIView.as_view()),
    path('cart-view/', store_views.CartAPIView.as_view()),
    path('cart-list/<str:cart_id>/<int:user_id>/', store_views.CartListView.as_view()),
    path('cart-list/<str:cart_id>/', store_views.CartListView.as_view()),
    path('cart-detail/<str:cart_id>/', store_views.CartDetailView.as_view()),
    path('cart-detail/<str:cart_id>/<int:user_id>/', store_views.CartDetailView.as_view()),
    path('cart-update/<str:cart_id>/<int:item_id>/', store_views.CartUpdateAPIView.as_view()),
    path('cart-delete/<str:cart_id>/<int:item_id>/', store_views.CartItemDeleteAPIView.as_view()),
    path('cart-delete/<str:cart_id>/<int:item_id>/<int:user_id>/', store_views.CartItemDeleteAPIView.as_view()),
    path('create-order/', store_views.createOrderAPIView.as_view()),
    path('checkout/<order_oid>/', store_views.CheckoutView.as_view()),
    path('coupon/', store_views.CouponAPIView.as_view()),
    path('create-review/', store_views.ReviewRatingAPIView.as_view(), name='create-review'),
    path('reviews/<product_id>/', store_views.ReviewListAPIView.as_view()),
    path('search/', store_views.SearchProductAPIView.as_view()),
    path('carousel/', CarouselImageList.as_view(), name='carousel-list'),
    path('offers-carousel/', OffersCarouselList.as_view(), name='product-carousel'),
    path('banners/', BannerListAPIView.as_view(), name='banner-list'),
    path('most-viewed-products/', MostViewedProductsAPIView.as_view(), name='most-viewed-products'),
    path('most-bought-products/', MostBoughtProductsAPIView.as_view(), name='most-bought-products'),

    #Payment Endpoints
    path('stripe-checkout/<order_oid>/', store_views.StripeCheckoutView.as_view()),
    path('payment-success/<order_oid>/', store_views.PaymentSuccessView.as_view()),
    
    # WhatsApp Checkout Endpoint
    path('whatsapp-checkout/', store_views.whatsapp_checkout, name='whatsapp_checkout'),

    #Customer Endpoint
    path('customer/orders/<user_id>/', customer_views.OrderAPIView.as_view()),
    path('customer/order/<user_id>/<order_oid>/', customer_views.OrderDetailAPIView.as_view()),
    path('customer/wishlist/<user_id>/', customer_views.WishlistAPIView.as_view()),
    path('customer/notification/<user_id>/', customer_views.CustomerNotificationAPIView.as_view()),
    path('customer/notification/<user_id>/<notification_id>/', customer_views.MarkCustomerNotificationAsSeenAPIView.as_view()),
    path('customer/setting/<int:pk>/', customer_views.CustomerUpdateView.as_view(), name='customer-settings'),
]