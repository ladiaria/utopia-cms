# Generated by Django 4.1.4 on 2024-09-17 18:52

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("comunidad", "0009_registro_issued_alter_circuito_general_quota_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="circuito",
            name="quota_type",
        ),
    ]