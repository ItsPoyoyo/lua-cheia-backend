from django.db import models
from vendor.models import Vendor
from userauths.models import User, Profile
from shortuuid.django_fields import ShortUUIDField
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

    
class Category(models.Model):
    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="category", default="category.jpg", null=True, blank=True)
    active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["title"]


class Product(models.Model):
    STATUS = (
        ('draft', 'Draft'),
        ('disabled', 'Disabled'),
        ('in_review', 'In Review'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="products", default="product.jpg", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    old_price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    shipping_ammount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    max_cart_limit = models.PositiveIntegerField(default=10)
    stock_qty = models.PositiveIntegerField(default=1)
    in_stock = models.BooleanField(default=True)
    status = models.CharField(max_length=100, choices=STATUS, default="published")
    views = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False)
    show_in_most_viewed = models.BooleanField(default=True, help_text="Show this product in the Most Viewed carousel")
    rating = models.PositiveIntegerField(default=0, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    pid = ShortUUIDField(unique=True, length=10, alphabet="abcdefghijklmnp12345")
    slug = models.SlugField(unique=True)
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        self.in_stock = self.stock_qty > 0
        self.rating = self.product_rating()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def product_rating(self):
        product_rating = Review.objects.filter(product=self).aggregate(avg_rating=models.Avg("rating"))
        return product_rating['avg_rating'] or 0

    def rating_count(self):
        return Review.objects.filter(product=self).count()

    def gallery(self):
        return Gallery.objects.filter(product=self)

    def specification(self):
        return Specification.objects.filter(product=self)

    def size(self):
        return Size.objects.filter(product=self)

    def color(self):
        return Color.objects.filter(product=self)

    def check_stock(self, color_name=None, size_name=None, quantity=1):
        """Check if product is available with given color/size combination"""
        if self.stock_qty < quantity:
            return (False, "Product is out of stock")
            
        if color_name and color_name != "No Color":
            try:
                color = self.colors.get(name=color_name)
                if color.stock_qty < quantity:
                    return (False, f"Color {color_name} is out of stock")
            except Color.DoesNotExist:
                return (False, f"Color {color_name} not available")
                
        if size_name and size_name != "No Size":
            try:
                size = self.sizes.get(name=size_name)
                if size.stock_qty < quantity:
                    return (False, f"Size {size_name} is out of stock")
            except Size.DoesNotExist:
                return (False, f"Size {size_name} not available")
                
        return (True, "In stock")

    def clean(self):
        if self.stock_qty < 0:
            raise ValidationError("Stock quantity cannot be negative")

    def update_stock(self, qty, color_name=None, size_name=None):
        """Update stock levels for product and optionally color/size"""
        if self.stock_qty < qty:
            raise ValueError("Not enough product stock available")
            
        self.stock_qty -= qty
        self.save()
        
        if color_name and color_name != "No Color":
            color = self.colors.get(name=color_name)
            if color.stock_qty < qty:
                raise ValueError(f"Not enough stock for color {color_name}")
            color.stock_qty -= qty
            color.save()
            
        if size_name and size_name != "No Size":
            size = self.sizes.get(name=size_name)
            if size.stock_qty < qty:
                raise ValueError(f"Not enough stock for size {size_name}")
            size.stock_qty -= qty
            size.save()


class Color(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='colors')
    name = models.CharField(max_length=1000)
    color_code = models.CharField(max_length=1000)
    image = models.FileField(upload_to="colors", default="color.jpg", null=True, blank=True)
    stock_qty = models.PositiveIntegerField(default=0)
    in_stock = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.product.title})"
    
    def save(self, *args, **kwargs):
        self.in_stock = self.stock_qty > 0
        super().save(*args, **kwargs)

    def clean(self):
        if self.stock_qty > self.product.stock_qty:
            raise ValidationError("Color stock cannot exceed product stock")


class Size(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    name = models.CharField(max_length=1000)
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    stock_qty = models.PositiveIntegerField(default=0)
    in_stock = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.product.title})"
    
    def save(self, *args, **kwargs):
        self.in_stock = self.stock_qty > 0
        super().save(*args, **kwargs)

    def clean(self):
        if self.stock_qty > self.product.stock_qty:
            raise ValidationError("Size stock cannot exceed product stock")


class Gallery(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery")
    color = models.ForeignKey(Color, on_delete=models.CASCADE, related_name='galleries', null=True, blank=True)
    image = models.FileField(upload_to="products", default="product.jpg")
    active = models.BooleanField(default=True)
    gid = ShortUUIDField(unique=True, length=10, alphabet="abcdefghijklmnp12345")

    def __str__(self):
        return self.color.name if self.color else "No Color"


class Specification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    content = models.CharField(max_length=1000)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Specifications"


class Cart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    qty = models.PositiveIntegerField(default=0)
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    sub_total = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    shipping_ammount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    service_fee = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    tax_fee = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    country = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    cart_id = models.CharField(max_length=1000, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart_id', 'product', 'color', 'size')

    def __str__(self):
        return f"{self.cart_id} - {self.product.title} - {self.color} - {self.size}"

    def clean(self):
        if self.qty > self.product.max_cart_limit:
            raise ValidationError(f"Quantity exceeds maximum limit of {self.product.max_cart_limit}")
        
        if self.color and self.color != "No Color":
            color = self.product.colors.filter(name=self.color).first()
            if color and color.stock_qty < self.qty:
                raise ValidationError(f"Only {color.stock_qty} available for color {self.color}")
        
        if self.size and self.size != "No Size":
            size = self.product.sizes.filter(name=self.size).first()
            if size and size.stock_qty < self.qty:
                raise ValidationError(f"Only {size.stock_qty} available for size {self.size}")


class CartOrder(models.Model):
    PAYMENT_STATUS = (
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('cancelled', 'Cancelled'),
    )
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    )

    vendor = models.ManyToManyField(Vendor, blank=True)
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="buyer", blank=True)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_ammount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    payment_status = models.CharField(choices=PAYMENT_STATUS, max_length=100, default="pending")
    order_status = models.CharField(choices=ORDER_STATUS, max_length=100, default="pending")
    initial_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    saved = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    full_name = models.CharField(max_length=1000, null=True, blank=True)
    email = models.CharField(max_length=1000, null=True, blank=True)
    phone = models.CharField(max_length=1000, null=True, blank=True)
    address = models.CharField(max_length=1000, null=True, blank=True)
    city = models.CharField(max_length=1000, null=True, blank=True)
    state = models.CharField(max_length=1000, null=True, blank=True)
    country = models.CharField(max_length=1000, null=True, blank=True)
    stripe_sesion_id = models.CharField(max_length=1000, blank=True, null=True)
    payment_method = models.CharField(max_length=100, default="stripe", blank=True, null=True)
    oid = ShortUUIDField(unique=True, length=10, alphabet="abcdefghijklmnp12345")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.oid
    
    def update_stock(self):
        """Update stock levels for all items in this order"""
        for item in self.orderitem.all():
            try:
                item.product.update_stock(
                    item.qty,
                    color_name=item.color,
                    size_name=item.size
                )
            except ValueError as e:
                raise ValidationError(f"Error updating stock for {item.product.title}: {str(e)}")
    
    def reduce_stock_for_whatsapp_order(self):
        """Reduce stock for WhatsApp orders when payment is confirmed by admin"""
        print("=" * 50)
        print(f"DEBUG: reduce_stock_for_whatsapp_order called for order {self.oid}")
        print(f"DEBUG: payment_method: {self.payment_method}")
        print(f"DEBUG: payment_status: {self.payment_status}")
        print(f"DEBUG: Method called at: {datetime.now()}")
        print("=" * 50)
        
        # Also log to file
        logger.info(f"reduce_stock_for_whatsapp_order called for order {self.oid}")
        logger.info(f"payment_method: {self.payment_method}, payment_status: {self.payment_status}")
        
        if self.payment_method == 'whatsapp' and self.payment_status == 'paid':
            print(f"DEBUG: Conditions met, proceeding with stock reduction")
            print(f"DEBUG: Order items count: {self.orderitem.count()}")
            
            for item in self.orderitem.all():
                try:
                    print(f"DEBUG: Processing item: {item.product.title}, qty: {item.qty}")
                    print(f"DEBUG: Current product stock: {item.product.stock_qty}")
                    print(f"DEBUG: Item color: '{item.color}' (type: {type(item.color)})")
                    print(f"DEBUG: Item size: '{item.size}' (type: {type(item.size)})")
                    print(f"DEBUG: Item ID: {item.id}")
                    
                    # Reduce product stock
                    product = item.product
                    old_stock = product.stock_qty
                    product.stock_qty -= item.qty
                    product.save()
                    
                    print(f"DEBUG: Product stock reduced from {old_stock} to {product.stock_qty}")
                    print(f"DEBUG: Product saved successfully: {product.title}")
                    
                    # Verify the stock was actually reduced
                    product.refresh_from_db()
                    print(f"DEBUG: Product stock after refresh: {product.stock_qty}")
                    
                    # Reduce color stock if specified
                    print(f"DEBUG: Checking color: '{item.color}' (type: {type(item.color)})")
                    if item.color and item.color != "No Color" and item.color.strip():
                        print(f"DEBUG: Looking for color with name: '{item.color}'")
                        color = product.colors.filter(name=item.color).first()
                        if color:
                            old_color_stock = color.stock_qty
                            color.stock_qty -= item.qty
                            color.save()
                            print(f"DEBUG: Color '{item.color}' stock reduced from {old_color_stock} to {color.stock_qty}")
                        else:
                            print(f"DEBUG: Color '{item.color}' not found for product {product.title}")
                            print(f"DEBUG: Available colors for this product: {[c.name for c in product.colors.all()]}")
                    else:
                        print(f"DEBUG: No color specified or color is 'No Color'")
                    
                    # Reduce size stock if specified
                    print(f"DEBUG: Checking size: '{item.size}' (type: {type(item.size)})")
                    if item.size and item.size != "No Size" and item.size.strip():
                        print(f"DEBUG: Looking for size with name: '{item.size}'")
                        size = product.sizes.filter(name=item.size).first()
                        if size:
                            old_size_stock = size.stock_qty
                            size.stock_qty -= item.qty
                            size.save()
                            print(f"DEBUG: Size '{item.size}' stock reduced from {old_size_stock} to {size.stock_qty}")
                        else:
                            print(f"DEBUG: Size '{item.size}' not found for product {product.title}")
                            print(f"DEBUG: Available sizes for this product: {[s.name for s in product.sizes.all()]}")
                    else:
                        print(f"DEBUG: No size specified or size is 'No Size'")
                            
                except Exception as e:
                    print(f"DEBUG: Error reducing stock for item {item.product.title}: {e}")
                    raise ValidationError(f"Error reducing stock for {item.product.title}: {str(e)}")
            
            print(f"DEBUG: Stock reduction completed successfully for order {self.oid}")
            return True
        else:
            error_msg = f"This method can only be used for paid WhatsApp orders. Current: method={self.payment_method}, status={self.payment_status}"
            print(f"DEBUG: {error_msg}")
            raise ValidationError(error_msg)


class CartOrderItem(models.Model):
    order = models.ForeignKey(CartOrder, on_delete=models.CASCADE, related_name="orderitem")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_item")
    qty = models.IntegerField(default=0)
    color = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_ammount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    country = models.CharField(max_length=100, null=True, blank=True)
    initial_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    saved = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    coupon = models.ManyToManyField("store.Coupon", blank=True)
    oid = ShortUUIDField(length=10, max_length=25, alphabet="abcdefghijklmnopqrstuvxyz")
    date = models.DateTimeField(auto_now_add=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "Cart Order Items"
        ordering = ["-date"]

    def __str__(self):
        return self.oid


class ProductFaq(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    email = models.EmailField(null=True, blank=True)
    question = models.CharField(max_length=1000)
    answer = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name_plural = "Product FAQs"


class Review(models.Model):
    RATING = (
        (1, '1 Star'),
        (2, '2 Star'),
        (3, '3 Star'),
        (4, '4 Star'),
        (5, '5 Star'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    review = models.TextField()
    reply = models.TextField(null=True, blank=True)
    rating = models.IntegerField(default=None, choices=RATING)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product.title

    class Meta:
        verbose_name_plural = "Reviews & Ratings"

    def profile(self):
        return Profile.objects.get(user=self.user)


@receiver(post_save, sender=Review)
def update_product_rating(sender, instance, **kwargs):
    if instance.product:
        instance.product.save()


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return self.product.title


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(CartOrder, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    order_item = models.ForeignKey(CartOrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    seen = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        if self.order:
            return self.order.oid
        else:
            return f"Notification - {self.pk}"


class Coupon(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    user_by = models.ManyToManyField(User, blank=True)
    code = models.CharField(max_length=1000)
    discount = models.IntegerField(default=1)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
    
    class Meta:
        verbose_name_plural = "Coupons"
        ordering = ['-id']


class Tax(models.Model):
    country = models.CharField(max_length=100)
    rate = models.IntegerField(default=5, help_text="Numbers added here are in percentage")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.country

    class Meta:
        verbose_name_plural = "Taxes"
        ordering = ['country']


class CarouselImage(models.Model):
    image = models.ImageField(upload_to='carousel/')
    caption = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.caption or f"Carousel Image {self.id}"


class OffersCarousel(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='carousels')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title or f"Carousel {self.id}"


class Banner(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')
    link = models.URLField(max_length=1000, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Banner {self.id}"