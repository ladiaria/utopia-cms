# Future Refactors

This document tracks pending refactors. Each item includes a checkbox — mark it when done.
Once all items are checked, clean up this document by removing completed entries.

See also [`REDESIGNV4.md`](REDESIGNV4.md) for deploy-time steps related to the v4 redesign.

## Checklist

- [ ] Migrate `render_article_card` to `render_card`
- [ ] Remove `article_card_new.html`
- [ ] Replace opaque size codes in `render_article_card`
- [ ] Unify card rendering in the redesign
- [ ] Clean up `art_count_` class in `section_row.html`
- [ ] Fix `ld-card__section` inside `article__section-label`
- [ ] Remove cover.html system (see `utopia_cms_ladiaria/docs/redesignv4.md`)
- [ ] Evaluate and remove `render_collectionrow` from `category/detail.html`
- [ ] Audit and replace/remove all uses of the `footer-section` class
- [ ] Remove Materialize CSS grid (`row` / `col s12`) from subscribe and login templates
- [ ] Remove all Materialize CSS dependencies from the project

---

## 1. Migrate `render_article_card` to `render_card`

Replace all uses of the old `render_article_card` tag with the new `render_card` tag, which uses
descriptive `variant=` names instead of opaque size codes.

```django
{# Old #}
{% render_article_card article=article media=article.home_display card_size="FN" %}

{# New #}
{% render_card article=article variant="article_card" %}
```

Once fully migrated, `render_article_card` can be removed from `core_tags.py`.

---

## 2. Remove `article_card_new.html`

After migrating all `card_size="FN"` usages to `render_card`, `article_card_new.html` becomes
obsolete and can be deleted.

---

## 3. Replace opaque size codes in `render_article_card`

The existing size codes (`FN`, `FD`, `FF`, `BG`, `MD`, `SM`, `OC`, `FW`) are not self-explanatory.
As part of the migration to `render_card`, each code should be mapped to a descriptive variant name.

| Code | Template | Suggested variant name |
|------|----------|------------------------|
| `FN` | `article_card_new.html` | `article_card` |
| `FD` | `card_full_detailed.html` | `card_full_detailed` |
| `FF` | `card_big_new.html` | `card_big_new` |
| `BG` | `card_big.html` | `card_big` |
| `MD` | `card_medium.html` | `card_medium` |
| `SM` | `card_small.html` | `card_small` |
| `FW` | `card_full.html` | `card_full` |
| `OC` | `card_big.html` | `card_big` |

---

## 4. Unify card rendering in the redesign

Several places in the redesign render cards item by item instead of using `render_card`.
These should be refactored to use the tag for consistency.

---

## 5. Clean up `art_count_` class in `section_row.html`

The wrapper `<div class="art_count_{{ art_count }}">` in `section_row.html` is a legacy pattern.
Evaluate whether it is still used by any CSS or JS and remove it if not.

---

## 6. Fix `ld-card__section` inside `article__section-label`

`publication_section` still outputs markup using the old `ld-card__section` class, which is
inconsistent with the new `article__*` class naming convention introduced in `article_card.html`.
The tag output and its CSS should be updated to match the new convention.

---

## 7. Remove cover.html system (la diaria)

See `utopia_cms_ladiaria/docs/redesignv4.md` for details.

---

## 8. Evaluate and remove `render_collectionrow` from `category/detail.html`

`category/detail.html` lines 189–199 renderizan un bloque de colecciones con `render_collectionrow`.
Evaluar si el feature de colecciones sigue en uso en el rediseño v4. Si no, eliminar el bloque del
template y el tag asociado.

---

## 9. Audit and replace/remove all uses of the `footer-section` class

La clase `footer-section` pertenece al diseño viejo. Auditar todos los templates que la usan y
determinar para cada uno si se elimina o se reemplaza por el equivalente del nuevo diseño.

```bash
grep -r "footer-section" --include="*.html" .
```

---

## 10. Remove Materialize CSS grid from subscribe and login templates

Los templates de suscripción y login usan el sistema de grilla de Materialize (`row` / `col s12`).
Estos wrappers ya no aportan nada en el rediseño y añaden capas innecesarias de HTML.
Eliminarlos de todos los templates afectados y ajustar el SCSS correspondiente.

```bash
grep -r "col s12\|class=\"row\"" --include="*.html" portal/apps/thedaily/templates/
```

---

## 11. Remove all Materialize CSS dependencies from the project

Materialize CSS fue el framework de estilos original del proyecto. El rediseño v4 reemplaza su
sistema de grilla, componentes y utilitarios por CSS propio. Una vez que el rediseño esté completo,
se deben eliminar todas las dependencias de Materialize:

- Remover las importaciones de Materialize en los archivos SCSS (`@import "utopia_materialize/..."`)
- Eliminar los bloques `{% block materialize_forms_css %}` y `{% block materialize_scripts %}` de
  los templates base y sus overrides
- Remover la app `crispy_forms_materialize` y su template pack de `INSTALLED_APPS` y settings
- Eliminar los archivos SCSS de `static/sass/utopia_materialize/`
- Auditar y reemplazar clases de Materialize residuales en templates (`.waves-effect`, `.z-depth-*`,
  `.input-field`, `.validate`, etc.)

```bash
grep -r "materialize\|utopia_materialize\|waves-effect\|z-depth\|input-field" \
  --include="*.html" --include="*.scss" --include="*.py" .
```
