# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0038_delete_mostviewedcarousel'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartorder',
            name='payment_method',
            field=models.CharField(blank=True, default='stripe', max_length=100, null=True),
        ),
    ]









