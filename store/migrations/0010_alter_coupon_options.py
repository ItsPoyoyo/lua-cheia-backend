# Generated by Django 4.2 on 2024-12-21 21:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_cartorderitem_coupon_alter_cartorder_address_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='coupon',
            options={'verbose_name_plural': 'Coupons'},
        ),
    ]
