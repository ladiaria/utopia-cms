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
