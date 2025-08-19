from django.core.management.base import BaseCommand
from django.utils import timezone
from store.models import CartOrder, User
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Simulate new cart orders for testing the live feed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of orders to create'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Sample customer data
        customers = [
            {'name': 'John Doe', 'email': 'john@example.com', 'phone': '+1234567890', 'city': 'New York', 'country': 'USA'},
            {'name': 'Jane Smith', 'email': 'jane@example.com', 'phone': '+0987654321', 'city': 'Los Angeles', 'country': 'USA'},
            {'name': 'Carlos Rodriguez', 'email': 'carlos@example.com', 'phone': '+1122334455', 'city': 'Miami', 'country': 'USA'},
            {'name': 'Maria Garcia', 'email': 'maria@example.com', 'phone': '+1555666777', 'city': 'Chicago', 'country': 'USA'},
            {'name': 'David Wilson', 'email': 'david@example.com', 'phone': '+1888999000', 'city': 'Houston', 'country': 'USA'},
        ]
        
        payment_statuses = ['pending', 'paid', 'failed', 'processing']
        order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        
        for i in range(count):
            customer = random.choice(customers)
            payment_status = random.choice(payment_statuses)
            order_status = random.choice(order_statuses)
            
            # Random total between $10 and $500
            total = Decimal(random.uniform(10.0, 500.0)).quantize(Decimal('0.01'))
            
            order = CartOrder.objects.create(
                buyer=user,
                full_name=customer['name'],
                email=customer['email'],
                phone=customer['phone'],
                address=f'{random.randint(100, 9999)} Main St',
                city=customer['city'],
                state='CA',
                country=customer['country'],
                payment_status=payment_status,
                order_status=order_status,
                sub_total=total * Decimal('0.8'),
                shipping_ammount=Decimal('10.00'),
                tax_fee=total * Decimal('0.1'),
                service_fee=Decimal('5.00'),
                total=total,
                date=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created order {order.oid} for {customer["name"]} - ${total} - {payment_status}/{order_status}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} test order(s)')
        )



