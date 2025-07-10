from django.core.management.base import BaseCommand
from store.permissions import create_vendedores_group


class Command(BaseCommand):
    help = 'Setup vendedores group with appropriate permissions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up vendedores permissions...'))
        
        try:
            group = create_vendedores_group()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created/updated vendedores group with {group.permissions.count()} permissions'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up permissions: {str(e)}')
            )

