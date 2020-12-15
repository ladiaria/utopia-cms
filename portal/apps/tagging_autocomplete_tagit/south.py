from south.modelsinspector import add_introspection_rules
from django.conf import settings

if "tagging_autocomplete_tagit" in settings.INSTALLED_APPS:
    try:
        from tagging_autocomplete_tagit.models import TagAutocompleteTagItField
    except ImportError:
        pass
    else:
        rules = [
            (
                (TagAutocompleteTagItField, ),
                [],
                {
                    "blank": ["blank", {"default": True}],
                    "max_length": ["max_length", {"default": 255}],
                    "max_tags": ["max_tags", {"default": False}],
                },
            ),
        ]
        add_introspection_rules(rules, ["^tagging_autocomplete_tagit\.models",])