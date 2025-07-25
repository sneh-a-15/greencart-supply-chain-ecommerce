# Generated by Django 5.1.2 on 2024-11-07 11:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_productcategories_product_image_and_more'),
        ('store', '0013_alter_fullorder_id_alter_orderitem_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.product'),
        ),
        migrations.DeleteModel(
            name='ProductCategories',
        ),
        migrations.DeleteModel(
            name='Product',
        ),
    ]
