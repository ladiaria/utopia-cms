# Generated by Django 4.1.4 on 2023-08-28 00:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('photologue_ladiaria', '0002_photoextended_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agency',
            name='info',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='email'),
        ),
    ]
