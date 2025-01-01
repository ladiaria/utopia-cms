# Generated by Django 4.1.13 on 2024-11-02 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comunidad", "0014_alter_subscriberarticle_audio_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriberarticle",
            name="to_be_published",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="programar publicación"
            ),
        ),
    ]