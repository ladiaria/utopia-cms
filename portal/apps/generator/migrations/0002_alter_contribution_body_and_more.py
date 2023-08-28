# Generated by Django 4.1.4 on 2023-08-28 00:24

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('generator', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contribution',
            name='body',
            field=models.TextField(verbose_name='cuerpo'),
        ),
        migrations.AlterField(
            model_name='contribution',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='fecha de creación'),
        ),
        migrations.AlterField(
            model_name='contribution',
            name='headline',
            field=models.CharField(max_length=100, verbose_name='título'),
        ),
        migrations.AlterField(
            model_name='contribution',
            name='user',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='contributions', to=settings.AUTH_USER_MODEL, verbose_name='usuario'),
        ),
    ]