# Generated by Django 4.1.4 on 2023-08-28 00:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('epubparser', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='epubfile',
            name='f',
            field=models.FileField(upload_to='epubparser/%Y/%m/%d'),
        ),
    ]
