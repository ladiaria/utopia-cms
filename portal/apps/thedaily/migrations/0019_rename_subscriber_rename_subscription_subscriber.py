# Generated by Django 4.1.13 on 2025-01-15 23:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("thedaily", "0018_remove_subscription_subscriber_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="subscription",
            old_name="subscriber_rename",
            new_name="subscriber",
        ),
    ]
