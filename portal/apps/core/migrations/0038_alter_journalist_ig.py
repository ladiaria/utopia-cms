# Generated by Django 4.1.4 on 2024-05-30 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_category_newsletter_extra_context'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalist',
            name='ig',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='instagram'),
        ),
    ]