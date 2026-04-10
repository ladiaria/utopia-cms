# Redesign v4 — Pasos para el deploy

Acciones manuales a realizar en el momento del deploy del nuevo diseño.

## Limpiar `local_settings.py`

Settings que quedaron sin consumidor tras eliminar código de la home vieja (homev3):

- `HOMEV3_CATEGORY_ROW_DEFAULT_LIMIT` — usada por `render_category_row`, tag eliminado
- `HOMEV3_CATEGORIES_ROW_CUSTOM_TEMPLATES` — usada por `RenderCategoryRowNode`, clase eliminada
- `HOMEV3_FEATURED_PUBLICATIONS_TEMPLATE_DIR` — usada por `render_publication_grid`, que solo se invoca desde `homev3/index.html` (home vieja)
- `ARTICLES_SLIDER_TEMPLATE_DIR` — usada por `get_articles_slider_template`, función eliminada
