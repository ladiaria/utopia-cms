from content_settings.types.basic import SimpleBool

# from django.forms import BooleanField, CheckboxInput (N1)


# Note about commented lines marked with '(N1)':
#     It was a successful attempt to show a checkbox widget but the bottom native help text still says that possible
#     values are strings, with no documented option to change or remove that text, (upstream bug?). That's why it was
#     rollbacked and kept commented. (SubNote: not tested default value, might need a change to the bool value True)
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
    # cls_field=BooleanField, (N1)
    # widget=CheckboxInput, (N1)
)
