# Generated by Django 4.1.4 on 2024-07-25 23:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comunidad", "0004_alter_subscriberarticle_audio_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscriberarticle",
            name="is_published",
            field=models.BooleanField(
                db_index=True, default=True, verbose_name="publicado"
            ),
        ),
    ]
