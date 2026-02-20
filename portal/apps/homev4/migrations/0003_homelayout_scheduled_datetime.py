from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("homev4", "0002_alter_homelayout_options_alter_homelayout_created_and_more"),
    ]

    operations = [
        # Add new datetime field (nullable so existing rows are not broken)
        migrations.AddField(
            model_name="homelayout",
            name="scheduled_datetime",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="fecha y hora programada",
                help_text="Fecha y hora desde la que este layout está activo",
            ),
        ),
        # Remove old time-only field
        migrations.RemoveField(
            model_name="homelayout",
            name="scheduled_time",
        ),
        # Update ordering meta to use the new field
        migrations.AlterModelOptions(
            name="homelayout",
            options={
                "ordering": ["-scheduled_datetime"],
                "verbose_name": "layout de portada",
                "verbose_name_plural": "layouts de portada",
            },
        ),
    ]
