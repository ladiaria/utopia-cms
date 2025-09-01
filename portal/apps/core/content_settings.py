from content_settings.types.basic import SimpleString
from content_settings.types.markup import SimpleJSON

from django.utils.safestring import mark_safe


SOCIAL_PROFILES = SimpleJSON(
    (
        '{"default":['
        '{"facebook":{"href":"","label":""}},'
        '{"instagram":{"href":"","label": ""}},'
        '{"tiktok":{"href":"","label": ""}},'
        '{"x":{"href":"","label": ""}},'
        '{"youtube":{"href":"","label": ""}},'
        '{"whatsapp":{"href":"","label": ""}}]}'
    ),
    widget_attrs={"style": "font-family: monospace;"},
    help=(
        "Social profile links href property and label to be used in templates, array of lists indexed by a string key "
        "that can be any string, using the publication slug as a default. Each list contains a single element "
        "dictionary with the social network name as key and the href and label as values inside another dictionary."
    )
)
EDIT_NEWSLETTERS_URLNAME = SimpleString(
    default="edit_profile", help="URL name for the edit newsletters page linked in the newsletter footer"
)
EDIT_NEWSLETTERS_LINK_TEXT = SimpleString(
    default="Configurar todos sus newsletters",
    help="Text for the link to the edit newsletters page linked in the newsletter footer",
)
CRM_JSON_API_MAPPINGS_EXTRA = SimpleJSON(
    # TODO: format the help text to be more readable
    '[]',
    widget_attrs={"style": "font-family: monospace;"},
    help=mark_safe(
        "Extra CRM JSON API mappings to be used in the crm_json_api_mapping function"
        "Each mapping in the 'extra' list is a dictionary with the following keys:"
        "<ul>"
        "<li>json_path: The local absolute path to the JSON file to be used for results 'caching', string</li>"
        "<li>api_slug: The URL slug to be used in the crm_json_api_mapping function, string</li>"
        "<li>map_fields: The fields to be used in the crm_json_api_mapping function, list of strings</li>"
        "<li>key: The key to be used in the crm_mappings dictionary available in the apps module, string</li>"
        "</ul>"
    )
)
