# Generated by Django 4.1.4 on 2023-10-03 00:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thedaily', '0007_alter_subscriber_document'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='subscriber',
            options={'permissions': (('es_suscriptor_default', 'Es suscriptor actualmente'),), 'verbose_name': 'suscriptor', 'verbose_name_plural': 'suscriptores'},
        ),
    ]