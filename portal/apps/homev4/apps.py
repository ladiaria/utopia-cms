from django.apps import AppConfig
from django.db.models.signals import pre_save


def _deduplicate_grid_data(sender, instance, update_fields=None, **kwargs):
    """Guarantee deduplication consistency: resolve_layout_grid_data runs before every
    save that touches grid_data, so the DB always holds clean, deduplicated layout data
    regardless of which code path triggered the save."""
    if update_fields is not None and "grid_data" not in update_fields:
        # Only grid_data saves need resolving — skip pending_grid_data-only saves.
        return
    if not isinstance(instance.grid_data, dict):
        return
    from .views import resolve_layout_grid_data
    instance.grid_data = resolve_layout_grid_data(
        instance.grid_data,
        publication=instance.publication,
        layout=instance,
        dedup_populated=True,
    )


class Homev4Config(AppConfig):
    name = "homev4"
    verbose_name = "Portada"

    def ready(self):
        from .models import HomeLayout
        pre_save.connect(_deduplicate_grid_data, sender=HomeLayout)
