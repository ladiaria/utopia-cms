from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


DAY_CHOICES = [
    ("lv", "Lunes a Viernes"),
    ("lmjv", "Lunes, Miércoles, Jueves y Viernes"),
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
    0: ["lv", "lmjv", "lu"],
    1: ["lv", "ma"],
    2: ["lv", "lmjv", "mi"],
    3: ["lv", "lmjv", "ju"],
    4: ["lv", "lmjv", "vi"],
    5: ["sa"],
    6: ["do"],
}

# Reverse map: day choice code → set of weekdays it covers
_DAY_CODE_TO_WEEKDAYS = {}
for _wd, _codes in _WEEKDAY_TO_DAY_CODES.items():
    for _code in _codes:
        _DAY_CODE_TO_WEEKDAYS.setdefault(_code, set()).add(_wd)


class HomeLayout(models.Model):
    name = models.CharField("nombre", max_length=100)
    publication = models.ForeignKey("core.Publication", on_delete=models.CASCADE, verbose_name="publicación")
    day = models.CharField("día", max_length=4, choices=DAY_CHOICES, null=True, blank=True)
    start_time = models.TimeField("hora inicio", null=True, blank=True)
    end_time = models.TimeField("hora fin", null=True, blank=True)
    ends_next_day = models.BooleanField(
        "termina al día siguiente", default=False,
        help_text="Activar cuando el rango horario cruza la medianoche (ej: 15:00 del sábado → 06:00 del domingo)",
    )
    is_manual_override = models.BooleanField(
        "override manual", default=False,
        help_text="Cuando está activo, este layout tiene prioridad sobre los programados",
    )
    manual_override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="activado por", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="homev4_overrides",
    )
    grid_data = models.JSONField("datos del layout", default=list, blank=True, help_text="Layout serializado de GridStack")
    pending_grid_data = models.JSONField("layout pendiente 5am", null=True, blank=True, default=None, help_text="Staging area escrito por el editor Preview 5am. La tarea programada lo mueve a grid_data a las 5am.")
    created = models.DateTimeField("creado", auto_now_add=True)
    modified = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        ordering = ["day", "start_time"]
        verbose_name = "programación de portada"
        verbose_name_plural = "programaciones de portada"

    def clean(self):
        if self.is_manual_override:
            conflict = HomeLayout.objects.filter(
                publication=self.publication, is_manual_override=True
            ).exclude(pk=self.pk).first()
            if conflict:
                raise ValidationError(
                    {"is_manual_override": f"Ya existe un override activo para esta publicación: \"{conflict.name}\". Desactivalo primero."}
                )
            return


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
        current_weekday = now.weekday()
        matching_days = _WEEKDAY_TO_DAY_CODES.get(current_weekday, [])

        # Also check previous day's layouts that end_next_day and haven't ended yet
        prev_weekday = (current_weekday - 1) % 7
        prev_matching_days = _WEEKDAY_TO_DAY_CODES.get(prev_weekday, [])

        candidates = []

        # Layouts from today that have already started
        today_candidates = cls.objects.filter(
            publication=publication,
            is_manual_override=False,
            day__in=matching_days,
            start_time__lte=current_time,
        ).order_by("-start_time")

        for layout in today_candidates:
            if layout.ends_next_day:
                # Starts today, ends tomorrow: active from start_time until midnight
                candidates.append(layout)
            elif layout.end_time is None or current_time <= layout.end_time:
                candidates.append(layout)

        # Layouts from yesterday that cross midnight and are still active
        prev_candidates = cls.objects.filter(
            publication=publication,
            is_manual_override=False,
            day__in=prev_matching_days,
            ends_next_day=True,
            end_time__gt=current_time,
        )

        for layout in prev_candidates:
            candidates.append(layout)

        return candidates[0] if candidates else None
