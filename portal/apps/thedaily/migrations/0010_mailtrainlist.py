# Generated by Django 4.1.4 on 2024-04-04 21:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thedaily', '0009_remainingcontent'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailtrainList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('list_cid', models.CharField(max_length=16, unique=True)),
                ('newsletter_name', models.CharField(max_length=64)),
                ('newsletter_tagline', models.CharField(blank=True, max_length=128, null=True)),
                ('newsletter_periodicity', models.CharField(blank=True, max_length=64, null=True)),
                ('on_signup', models.BooleanField(default=False, verbose_name='Activada para nuevas cuentas')),
                ('newsletter_new_pill', models.BooleanField(default=False, verbose_name='pill de "nuevo" para la newsletter en el perfil de usuario')),
            ],
        ),
    ]
