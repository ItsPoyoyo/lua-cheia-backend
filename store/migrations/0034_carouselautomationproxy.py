# Generated by Django 4.2 on 2025-07-09 22:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0033_alter_cartorderitem_options_color_in_stock_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarouselAutomationProxy',
            fields=[
            ],
            options={
                'verbose_name': 'Carousel Automation',
                'verbose_name_plural': 'Carousel Automation',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('store.offerscarousel',),
        ),
    ]
