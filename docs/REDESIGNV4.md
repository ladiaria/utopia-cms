# Redesign v4 — Pasos para el deploy

Acciones manuales a realizar en el momento del deploy del nuevo diseño.

## Deploy de `utopia-cms-library`

El rediseño de la portada de Libros y la Comunidad de libros incluye cambios en el template `book_detail.html` del repositorio `utopia-cms-library` (directorio separado: `web/utopia-cms-library/`). Este repo tiene su propio ciclo de deploy y hay que acordarse de incluirlo explícitamente.

## Limpiar `local_settings.py`

Settings que quedaron sin consumidor tras eliminar código de la home vieja (homev3):

- `HOMEV3_CATEGORY_ROW_DEFAULT_LIMIT` — usada por `render_category_row`, tag eliminado
- `HOMEV3_CATEGORIES_ROW_CUSTOM_TEMPLATES` — usada por `RenderCategoryRowNode`, clase eliminada
- `HOMEV3_FEATURED_PUBLICATIONS_TEMPLATE_DIR` — usada por `render_publication_grid`, que solo se invoca desde `homev3/index.html` (home vieja)
- `ARTICLES_SLIDER_TEMPLATE_DIR` — usada por `get_articles_slider_template`, función eliminada

## Revisar `HOME_NAV_ITEMS` en `local_settings.py`

Se agregó el setting `HOME_NAV_ITEMS` para controlar los items del navbar en la home (`/`). Por ahora los slugs de cada item son estimados — verificar que todas las URLs correspondan a las áreas/publicaciones/secciones reales antes del deploy.

El setting vive en `local_settings.py` cerca de `HOMEV3_EXCLUDE_MENU_PUBLICATIONS`. El template que lo consume es `thedaily/templates/navbar.html` (con fallback a `MENU_CATEGORIES` si el setting no existe).

## Migrar `CORE_ARTICLE_CARDS_SECTION_NAME_OVERRIDES` a template

El setting ahora soporta valores que sean paths a templates (terminados en `.html`), además de strings HTML inline. La sección "sobre la diaria" pasó a usar un template para poder evolucionar el markup sin tocar `local_settings.py`.

Cambiar:

```python
CORE_ARTICLE_CARDS_SECTION_NAME_OVERRIDES = {"sobre-la-diaria": "Sobre <strong>la diaria</strong>"}
```

por:

```python
CORE_ARTICLE_CARDS_SECTION_NAME_OVERRIDES = {
    "sobre-la-diaria": "utopia_cms_ladiaria/article/sobre_la_diaria_pill.html",
}
```

El template vive en `utopia_cms_ladiaria/templates/utopia_cms_ladiaria/article/sobre_la_diaria_pill.html` y recibe `section` y `article` en contexto.
