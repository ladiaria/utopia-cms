# Generated by Django 4.1.4 on 2024-08-05 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comunidad", "0006_subscriberarticle_full_restricted"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscriberarticle",
            name="deck",
            field=models.TextField(
                blank=True,
                help_text="Se muestra en la página del artículo debajo del título.",
                null=True,
                verbose_name="descripción",
            ),
        ),
        migrations.AlterField(
            model_name="subscriberarticle",
            name="home_top_deck",
            field=models.TextField(
                blank=True,
                help_text="Se muestra en los destacados de la portada, en el caso de estar vacío se muestra la bajada del artículo.",
                null=True,
                verbose_name="bajada en destacados",
            ),
        ),
    ]
