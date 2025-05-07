from content_settings.types.array import SimpleStringsList

from django.utils.safestring import mark_safe


PHOTOLOGUE_CROP2FIT_SIZES = SimpleStringsList(
    widget_attrs={"rows": 14, "style": "font-family: monospace;"},
    help=mark_safe(
        "Nombres de tamaños de imagen que se deben crear al ejecutar el command <code>utopiacms_photosizes</code> "
        "(uno por línea en formato <code>widthxheight</code>, se crearán si no existen y se les marcará el atributo "
        "<code>crop</code> en <code>True</code>). Ejemplo:<pre>80x80\n100x100\n300x169</pre>"
    ),
)
