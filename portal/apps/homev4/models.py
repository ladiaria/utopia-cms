from django.conf import settings
from django.db import models
from django.utils import timezone


DAY_CHOICES = [
    ("lv", "Lunes a Viernes"),
    ("sa", "Sábado"),
    ("do", "Domingo"),
    ("lu", "Lunes"),
    ("ma", "Martes"),
    ("mi", "Miércoles"),
    ("ju", "Jueves"),
    ("vi", "Viernes"),
]

# Maps Python weekday() (0=Monday … 6=Sunday) to matching day choice codes
_WEEKDAY_TO_DAY_CODES = {
    0: ["lv", "lu"],
    1: ["lv", "ma"],
    2: ["lv", "mi"],
    3: ["lv", "ju"],
    4: ["lv", "vi"],
    5: ["sa"],
    6: ["do"],
}


class HomeLayout(models.Model):
    name = models.CharField("nombre", max_length=100)
    publication = models.ForeignKey("core.Publication", on_delete=models.CASCADE, verbose_name="publicación")
    day = models.CharField("día", max_length=2, choices=DAY_CHOICES, null=True, blank=True)
    start_time = models.TimeField("hora inicio", null=True, blank=True)
    end_time = models.TimeField("hora fin", null=True, blank=True)
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
        ordering = ["day", "start_time"]
        verbose_name = "layout de portada"
        verbose_name_plural = "layouts de portada"

    def __str__(self):
        override = " [OVERRIDE]" if self.is_manual_override else ""
        day_label = self.get_day_display() or "—"
        start = self.start_time.strftime("%H:%M") if self.start_time else "?"
        end = self.end_time.strftime("%H:%M") if self.end_time else "?"
        return f"{self.name} ({self.publication} — {day_label} {start}–{end}){override}"

    @classmethod
    def get_active_layout(cls, publication):
        """Return the active layout for the current day and time."""
        # Manual override takes priority
        manual = cls.objects.filter(publication=publication, is_manual_override=True).first()
        if manual:
            return manual

        now = timezone.localtime()
        current_time = now.time()
        matching_days = _WEEKDAY_TO_DAY_CODES.get(now.weekday(), [])

        # Get candidates: matching day and already started
        candidates = cls.objects.filter(
            publication=publication,
            is_manual_override=False,
            day__in=matching_days,
            start_time__lte=current_time,
        ).order_by("-start_time")

        # Return the first candidate whose end_time hasn't passed (None = no end)
        for layout in candidates:
            if layout.end_time is None or current_time <= layout.end_time:
                return layout
        return None
