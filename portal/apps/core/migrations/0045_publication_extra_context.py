# Generated by Django 4.1.4 on 2024-08-23 00:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0044_section_included_in_category_menu"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="extra_context",
            field=models.JSONField(
                default=dict,
                help_text='Diccionario Python en formato JSON que se utilizará como contexto al inicio de la construcción del contexto predeterminado, sus entradas, si hay colisión, serían sobreescritas por la vista de portada en backend o comando de envío de newsletter.<br>Ejemplo: <code>{"custom_footer_msg": "Esta newsletter fue generada utilizando utopia-cms"}</code>',
                verbose_name="Contexto extra para portadas y newsletter",
            ),
        ),
    ]
