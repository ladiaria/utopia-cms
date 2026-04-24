from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("homev4", "0008_add_pending_grid_data"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeLayoutAuditLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="fecha")),
                ("triggered_by", models.CharField(choices=[("editor", "Editor"), ("celery:5am", "Tarea 5am"), ("celery:refresh", "Tarea refresh")], max_length=20, verbose_name="origen")),
                ("block_key", models.CharField(db_index=True, max_length=50, verbose_name="bloque")),
                ("ids_before", models.JSONField(default=list, verbose_name="IDs anteriores")),
                ("ids_after", models.JSONField(default=list, verbose_name="IDs nuevos")),
                ("layout", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_logs", to="homev4.homelayout", verbose_name="layout")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name="usuario")),
            ],
            options={
                "verbose_name": "registro de auditoría",
                "verbose_name_plural": "registros de auditoría",
                "ordering": ["-timestamp"],
            },
        ),
    ]
