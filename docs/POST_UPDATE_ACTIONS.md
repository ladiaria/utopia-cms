## Artículos en borrador causan 500 en la vista de detalle

**Fecha detectado:** 2026-05-17
**Branch:** trello4032

Varios métodos de `ArticleBase` en `models.py` asumen que `date_published` nunca es `None`, pero los artículos en borrador no tienen fecha de publicación. Esto causaba errores 500 al intentar previsualizar un artículo desde el admin.

**Parches aplicados (workaround):**
- `datetime_isoformat` en `core/utils.py`: guard contra `None`
- `datetime_published_verbose` en `models.py`: guard contra `None`, retorna `''`
- `date_published_verbose` en `models.py`: guard contra `None`, retorna `''`

**Por revisar:**
- Determinar si hay más métodos de `ArticleBase` que asumen `date_published is not None`
- Evaluar si la vista `article_detail` debería cortar antes para borradores (redirigir o mostrar 404/403 en lugar de intentar renderizar el template completo)
- Revisar `date_published_seconds_ago` que también explotaría con `None`
