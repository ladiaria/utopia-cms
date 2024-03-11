# Generated by Django 4.1.4 on 2024-03-04 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_alter_category_name_alter_category_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='newsletter_from_email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name="email en el 'From' del mensaje"),
        ),
        migrations.AddField(
            model_name='category',
            name='newsletter_from_name',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name="nombre en el 'From' del mensaje"),
        ),
    ]
