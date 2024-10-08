# Generated by Django 4.1.4 on 2024-07-06 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0040_alter_article_is_published_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="full_restricted",
            field=models.BooleanField(
                default=False,
                help_text="Acceso solamente a usuarios que tengan alguna suscripción activa.",
                verbose_name="Disponible sólo para suscriptores",
            ),
        ),
    ]
