# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-15 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20210531_0242'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='exclude_from_top_menu',
            field=models.BooleanField(default=False, verbose_name='Excluir \xedtem en men\xfa superior de escritorio'),
        ),
    ]
