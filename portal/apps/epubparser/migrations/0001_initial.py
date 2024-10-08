# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-08-20 04:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EpubFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('f', models.FileField(upload_to=b'epubparser/%Y/%m/%d')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Section')),
            ],
        ),
    ]
