from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from store.permissions import setup_vendor_permissions

class Command(BaseCommand):
    help = 'Set up vendor group and permissions'

    def handle(self, *args, **options):
        self.stdout.write('Setting up vendor group and permissions...')
        
        try:
            # Create vendor group with permissions
            vendor_group = setup_vendor_permissions()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created vendor group "{vendor_group.name}" with {vendor_group.permissions.count()} permissions'
                )
            )
            
            # Show what permissions vendors have
            self.stdout.write('\nVendor permissions:')
            for permission in vendor_group.permissions.all():
                self.stdout.write(f'  - {permission.content_type.app_label}.{permission.content_type.model}: {permission.codename}')
            
            self.stdout.write('\nTo add a user as a vendor:')
            self.stdout.write('  1. Go to Django admin')
            self.stdout.write('  2. Edit the user')
            self.stdout.write('  3. Add them to the "Vendors" group')
            self.stdout.write('  4. Set is_staff = True (so they can access admin)')
            self.stdout.write('  5. Set is_superuser = False (for security)')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up vendor group: {e}')
            )
