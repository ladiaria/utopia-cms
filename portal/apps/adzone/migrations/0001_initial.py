# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-08-20 04:12
from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdBase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('url', models.URLField(help_text='Siempre debe comenzar con http:// o https:// y si se necesita un timestamp usar %(timestamp)d', verbose_name='Advertised URL')),
                ('mobile_url', models.URLField(blank=True, help_text='\xcddem anterior. Si es la misma dejar en blanco.', null=True, verbose_name='Alternative Advertised URL for mobile.')),
                ('analytics_tracking', models.CharField(blank=True, max_length=255, verbose_name='Trackeo analytics')),
                ('since', models.DateTimeField(auto_now_add=True, verbose_name='Since')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Updated')),
                ('start_showing', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Start showing')),
                ('stop_showing', models.DateTimeField(default=datetime.datetime(9999, 12, 29, 23, 59, 59, 999999, tzinfo=datetime.timezone.utc), verbose_name='Stop showing')),
            ],
            options={
                'verbose_name': 'Ad Base',
                'verbose_name_plural': 'Ad Bases',
            },
        ),
        migrations.CreateModel(
            name='AdCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(unique=True, verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='AdClick',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('click_date', models.DateTimeField(auto_now_add=True, verbose_name='When')),
                ('source_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='Who')),
            ],
            options={
                'verbose_name': 'Ad Click',
                'verbose_name_plural': 'Ad Clicks',
            },
        ),
        migrations.CreateModel(
            name='AdImpression',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('impression_date', models.DateTimeField(auto_now_add=True, verbose_name='When')),
                ('source_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='Who')),
            ],
            options={
                'verbose_name': 'Ad Impression',
                'verbose_name_plural': 'Ad Impressions',
            },
        ),
        migrations.CreateModel(
            name='Advertiser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=255, verbose_name='Company Name')),
                ('website', models.URLField(verbose_name='Company Site')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('company_name',),
                'verbose_name': 'Ad Provider',
                'verbose_name_plural': 'Advertisers',
            },
        ),
        migrations.CreateModel(
            name='AdZone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(verbose_name='Slug')),
                ('description', models.TextField(verbose_name='Description')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Zone',
                'verbose_name_plural': 'Zones',
            },
        ),
        migrations.CreateModel(
            name='BannerAd',
            fields=[
                ('adbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='adzone.AdBase')),
                ('content', models.ImageField(help_text=b'Dimensiones: 970\xc3\x97250px</br>Tama\xc3\xb1o m\xc3\xa1ximo permitido: 150kb</br>Formato: JPG, GIF, PNG', upload_to=b'adzone/bannerads/', verbose_name='Banner escritorio')),
                ('mobile_content', models.ImageField(blank=True, help_text=b'Dimensiones: 300\xc3\x97250px</br>Tama\xc3\xb1o m\xc3\xa1ximo permitido: 150kb</br>Formato: JPG, GIF, PNG', null=True, upload_to=b'adzone/bannerads/', verbose_name='Banner m\xf3vil')),
            ],
            bases=('adzone.adbase',),
        ),
        migrations.CreateModel(
            name='TextAd',
            fields=[
                ('adbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='adzone.AdBase')),
                ('content', models.TextField(verbose_name='Content')),
            ],
            bases=('adzone.adbase',),
        ),
        migrations.AddField(
            model_name='adimpression',
            name='ad',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adzone.AdBase'),
        ),
        migrations.AddField(
            model_name='adclick',
            name='ad',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adzone.AdBase'),
        ),
        migrations.AddField(
            model_name='adbase',
            name='advertiser',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adzone.Advertiser', verbose_name='Ad Provider'),
        ),
        migrations.AddField(
            model_name='adbase',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='adzone.AdCategory', verbose_name='Category'),
        ),
        migrations.AddField(
            model_name='adbase',
            name='sites',
            field=models.ManyToManyField(to='sites.Site', verbose_name='Sites'),
        ),
        migrations.AddField(
            model_name='adbase',
            name='zone',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adzone.AdZone', verbose_name='Zone'),
        ),
    ]
