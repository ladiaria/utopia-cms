# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-10-17 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_auto_20221117_0412'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='html_title',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name="contenido del tag <title> y del metadato 'og:title' del código HTML"),
        ),
        migrations.AddField(
            model_name='category',
            name='meta_description',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name="contenido del metadato 'description' y 'og:description' del código HTML"),
        ),
        migrations.AddField(
            model_name='publication',
            name='html_title',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name="contenido del tag <title> y del metadato 'og:title' del código HTML"),
        ),
        migrations.AddField(
            model_name='publication',
            name='meta_description',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name="contenido del metadato 'description' y 'og:description' del código HTML"),
        ),
        migrations.AddField(
            model_name='section',
            name='html_title',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name="contenido del tag <title> y del metadato 'og:title' del código HTML"),
        ),
        migrations.AddField(
            model_name='section',
            name='meta_description',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name="contenido del metadato 'description' y 'og:description' del código HTML"),
        ),
    ]
