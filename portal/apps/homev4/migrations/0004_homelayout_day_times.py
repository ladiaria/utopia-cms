from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("homev4", "0003_homelayout_scheduled_datetime"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="homelayout",
            name="scheduled_datetime",
        ),
        migrations.AddField(
            model_name="homelayout",
            name="day",
            field=models.CharField(
                blank=True,
                choices=[
                    ("lv", "Lunes a Viernes"),
                    ("sa", "Sábado"),
                    ("do", "Domingo"),
                    ("lu", "Lunes"),
                    ("ma", "Martes"),
                    ("mi", "Miércoles"),
                    ("ju", "Jueves"),
                    ("vi", "Viernes"),
                ],
                max_length=2,
                null=True,
                verbose_name="día",
            ),
        ),
        migrations.AddField(
            model_name="homelayout",
            name="start_time",
            field=models.TimeField(blank=True, null=True, verbose_name="hora inicio"),
        ),
        migrations.AddField(
            model_name="homelayout",
            name="end_time",
            field=models.TimeField(blank=True, null=True, verbose_name="hora fin"),
        ),
        migrations.AlterModelOptions(
            name="homelayout",
            options={
                "ordering": ["day", "start_time"],
                "verbose_name": "layout de portada",
                "verbose_name_plural": "layouts de portada",
            },
        ),
    ]
