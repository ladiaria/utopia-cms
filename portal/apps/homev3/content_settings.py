from content_settings.types.array import SimpleStringsList


FEATURED_CATEGORIES = SimpleStringsList(
    widget_attrs={"style": "font-family: monospace;"},
    help=("Slugs de áreas que se mostrarán en la portada principal en el orden que se ingresen en esta lista."),
)
