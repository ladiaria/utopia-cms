# Generated by Django 4.1.13 on 2024-12-18 21:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("photologue", "0013_alter_watermark_image"),
        ("videologue", "0002_alter_video_byline_alter_video_caption_and_more"),
        ("core", "0053_defaultnewsletter_defaultnewsletterarticle_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="alt_desc_metadata",
            field=models.TextField(
                blank=True,
                help_text="Aplica a metadatos: meta description, Open Graph y Schema en el<br>&lt;head&gt; de la página del artículo.<br>Si se deja vacío aplica Descripción principal.",
                null=True,
                verbose_name="descripción alternativa para metadatos",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="deck",
            field=models.TextField(
                blank=True,
                help_text="Se muestra en la página del artículo debajo del título y en demás lugares<br>del sitio que se muestre la descripción (a no ser que tenga una versión<br>alternativa activa que la reemplace).",
                null=True,
                verbose_name="descripción",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="header_display",
            field=models.CharField(
                blank=True,
                choices=[("FW", "Ancho completo"), ("BG", "Grande")],
                default="BG",
                max_length=2,
                null=True,
                verbose_name="estilo de cabezal",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="home_lead",
            field=models.TextField(
                blank=True,
                help_text="Se muestra en la portada principal (home).<br>Si se deja vacía aplica Descripción principal.",
                null=True,
                verbose_name="Descripción alternativa para portada principal (home)",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="photo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="photologue.photo",
                verbose_name="imagen principal",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="video",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="articles_%(app_label)s",
                to="videologue.video",
            ),
        ),
    ]
