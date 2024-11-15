# Generated by Django 4.1.13 on 2024-11-02 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_alter_categoryhomearticle_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="to_be_published",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="programar publicación"
            ),
        ),
    ]
