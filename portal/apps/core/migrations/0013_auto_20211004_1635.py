# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-10-04 16:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20210929_0202'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='articlerel',
            unique_together=set([('article', 'edition', 'section', 'position')]),
        ),
    ]
