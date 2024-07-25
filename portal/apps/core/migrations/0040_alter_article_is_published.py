# Generated by Django 4.1.4 on 2024-07-25 23:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_alter_edition_unique_together"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="is_published",
            field=models.BooleanField(
                db_index=True, default=True, verbose_name="publicado"
            ),
        ),
    ]
