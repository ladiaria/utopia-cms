from content_settings.types.basic import SimpleString
from content_settings.types.markup import SimpleJSON


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
