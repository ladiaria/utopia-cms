# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-12-03 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20211203_1110'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='fecha de creaci\xf3n'),
        ),
        migrations.AlterField(
            model_name='article',
            name='date_published',
            field=models.DateTimeField(db_index=True, null=True, verbose_name='fecha de publicaci\xf3n'),
        ),
    ]
