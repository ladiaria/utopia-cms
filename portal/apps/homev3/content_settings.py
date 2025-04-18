from content_settings.types.basic import SimpleBool


HOMEV3_ROWS_DUPLICATES_HOMETOP_ONLY = SimpleBool(
    default="true",
    help=(
        "Se utiliza para saber cuándo considerar que un artículo se debe o no incluir en una fila de contenido de "
        "área o sección de portada por ser un artículo ya mostrado en la página:"
        "<ul>"
        "<li>Si es <code>true</code>, se considera repetido solamente si aparece en los destacados de portada.</li>"
        "<li>Si es <code>false</code>, se considera repetido si aparece en los destacados de portada o en cualquier "
        "otra fila de contenido de área o sección.</li>"
        "</ul>"
    ),
)
