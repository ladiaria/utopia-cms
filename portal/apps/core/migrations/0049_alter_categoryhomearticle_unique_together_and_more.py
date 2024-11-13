# Generated by Django 4.1.13 on 2024-11-04 22:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_alter_article_audio_alter_article_created_by_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="categoryhomearticle",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="categoryhomearticle",
            name="article",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="home_articles",
                to="core.article",
                verbose_name="artículo",
            ),
        ),
    ]
