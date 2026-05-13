import copy
import logging

from django.apps import AppConfig
from django.db.models.signals import pre_save

logger = logging.getLogger(__name__)


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


def _update_crossword_in_layouts(sender, instance, **kwargs):
    """When a Crossword is saved, write its data into the crucigrama comp entry of
    every HomeLayout so build_home_data reads from grid_data with no per-request DB query.
    Uses bulk_update (no signals) to avoid triggering the pre_save dedup cycle."""
    from .models import HomeLayout

    image_url = instance.image.url if instance.image else None
    to_update = []
    for layout in HomeLayout.objects.all():
        if not isinstance(layout.grid_data, dict):
            continue
        gd = copy.deepcopy(layout.grid_data)
        for comp in gd.get("componentes", []):
            if comp.get("key") == "crucigrama":
                comp["crossword_id"] = instance.id
                comp["crossword_image_url"] = image_url
                comp["crossword_url"] = "/crucigramas/"
                layout.grid_data = gd
                to_update.append(layout)
                break
    if to_update:
        HomeLayout.objects.bulk_update(to_update, ["grid_data"])
        logger.info("_update_crossword_in_layouts: updated %d layouts for crossword id=%d", len(to_update), instance.id)


class Homev4Config(AppConfig):
    name = "homev4"
    verbose_name = "Portada"

    def ready(self):
        from .models import HomeLayout
        pre_save.connect(_deduplicate_grid_data, sender=HomeLayout)

        try:
            from utopia_cms_ladiaria.models import Crossword
            from django.db.models.signals import post_save
            post_save.connect(_update_crossword_in_layouts, sender=Crossword)
        except ImportError:
            pass
