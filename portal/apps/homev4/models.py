from django.conf import settings
from django.db import models
from django.utils import timezone


class HomeLayout(models.Model):
    name = models.CharField("nombre", max_length=100)
    publication = models.ForeignKey("core.Publication", on_delete=models.CASCADE, verbose_name="publicación")
    scheduled_time = models.TimeField("hora programada", help_text="Hora desde la que este layout está activo")
    is_manual_override = models.BooleanField(
        "override manual", default=False,
        help_text="Cuando está activo, este layout tiene prioridad sobre los programados",
    )
    manual_override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="activado por", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="homev4_overrides",
    )
    grid_data = models.JSONField("datos del layout", default=list, blank=True, help_text="Layout serializado de GridStack")
    created = models.DateTimeField("creado", auto_now_add=True)
    modified = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        ordering = ["-scheduled_time"]
        verbose_name = "layout de portada"
        verbose_name_plural = "layouts de portada"

    def __str__(self):
        override = " [OVERRIDE]" if self.is_manual_override else ""
        return f"{self.name} ({self.publication} @ {self.scheduled_time}){override}"

    @classmethod
    def get_active_layout(cls, publication):
        """Return the active layout based on current time, no Celery needed."""
        # Manual override takes priority
        manual = cls.objects.filter(publication=publication, is_manual_override=True).first()
        if manual:
            return manual
        # Find the scheduled layout for the current time
        current_time = timezone.localtime().time()
        return cls.objects.filter(
            publication=publication,
            is_manual_override=False,
            scheduled_time__lte=current_time,
        ).order_by("-scheduled_time").first()
