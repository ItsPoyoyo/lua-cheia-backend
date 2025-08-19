from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from vendor.models import Vendor

class Command(BaseCommand):
    help = 'Add a user as a vendor'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to make vendor')
        parser.add_argument('--name', type=str, help='Vendor shop name')
        parser.add_argument('--phone', type=str, help='Vendor phone number')

    def handle(self, *args, **options):
        email = options['email']
        shop_name = options.get('name', f'Shop {email.split("@")[0]}')
        phone = options.get('phone', '')

        try:
            # Find the user
            user = User.objects.get(email=email)
            
            # Add user to Vendors group
            vendor_group, created = Group.objects.get_or_create(name='Vendors')
            user.groups.add(vendor_group)
            
            # Make user staff (so they can access admin) but not superuser
            user.is_staff = True
            user.is_superuser = False
            user.save()
            
            # Create or update vendor profile
            vendor, created = Vendor.objects.get_or_create(
                user=user,
                defaults={
                    'name': shop_name,
                    'email': email,
                    'mobile': phone,
                    'active': True,
                }
            )
            
            if not created:
                vendor.name = shop_name
                vendor.email = email
                vendor.mobile = phone
                vendor.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully added {email} as a vendor!'
                )
            )
            self.stdout.write(f'  - User: {user.full_name or user.username}')
            self.stdout.write(f'  - Shop: {vendor.name}')
            self.stdout.write(f'  - Phone: {vendor.mobile}')
            self.stdout.write(f'  - Admin access: /admin/')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {email} not found!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error adding vendor: {e}')
            )
