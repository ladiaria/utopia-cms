# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-12-20 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('photologue', '0010_auto_20160105_1307'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photoeffect',
            name='filters',
            field=models.CharField(blank=True, help_text='Chain multiple filters using the following pattern "FILTER_ONE->FILTER_TWO->FILTER_THREE". Image filters will be applied in order. The following filters are available: BLUR, CONTOUR, DETAIL, EDGE_ENHANCE, EDGE_ENHANCE_MORE, EMBOSS, FIND_EDGES, Kernel, SHARPEN, SMOOTH, SMOOTH_MORE.', max_length=200, verbose_name='filters'),
        ),
    ]
