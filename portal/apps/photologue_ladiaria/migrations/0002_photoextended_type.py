# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-09-20 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('photologue_ladiaria', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='photoextended',
            name='type',
            field=models.CharField(choices=[('f', 'Foto'), ('i', 'Ilustración')], default='f', max_length=1, verbose_name='tipo'),
        ),
    ]
