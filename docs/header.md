# Header — tipos y comportamientos

El header está implementado principalmente en `utopia-cms`. Algunos elementos
(`fixed items`, `header-pill`) viven en la app externa `utopia_cms_ladiaria`
y se inyectan vía bloques de template.

El componente base es `portal/templates/header.html`.
Los estilos están en `static/sass/utopia_header.scss`.

---

## Estructura general

El header siempre tiene **2 filas**:

1. **Fila superior** (`.upper-content`): siempre 3 columnas —
   izquierda | centro | derecha.
2. **Fila inferior** (`.nav-content`): nav de áreas/secciones (puede estar
   ausente o colapsada según el tipo de header y el estado).

En el header de portada y áreas/publicaciones, la fila superior aparenta
ocupar más espacio en estado normal (logo grande, `padding-block` mayor)
gracias a CSS, sin necesidad de un nodo DOM extra.

---

## Clases CSS relevantes

| Clase / selector            | Cuándo se aplica                              |
|-----------------------------|-----------------------------------------------|
| `header.home-header`        | Portada                                       |
| `header.category-pub-header`| Páginas de área o publicación                 |
| `header.section-detail-header` | Detalle de sección                         |
| `body.article`              | Artículo                                      |
| `header.sticky`             | Cualquier header al hacer scroll              |
| `body.main-menu-open`       | Menú extendido abierto                        |

---

## 1. Header de portada (`header.home-header`)

### Desktop — estado normal

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa + fixed items  │  logo  │  search + login/suscribir│
│           nav de áreas y publicaciones                               │
└─────────────────────────────────────────────────────────────────────┘
```

- El logo está en la columna central de la fila superior, igual que en
  sticky. En estado normal se ve más grande y la fila tiene más
  `padding-block`, lo que genera el efecto visual de "logo prominente".
- `fixed items` proviene de `utopia_cms_ladiaria`.

### Desktop — sticky (al hacer scroll)

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa  │  logo  │  search + login/suscribir             │
└─────────────────────────────────────────────────────────────────────┘
```

- El logo reduce su `max-width` y el `padding-block` de la fila colapsa.
- El nav de áreas/publicaciones y los fixed items desaparecen.

### Mobile — estado normal

```
┌────────────────────────────────┐
│  menú hamburguesa │ logo │ search │
│  nav de áreas y publicaciones  │
└────────────────────────────────┘
```

### Mobile — sticky

```
┌────────────────────────────────┐
│  menú hamburguesa │ logo │ search │
└────────────────────────────────┘
```

- Desaparece el nav.

---

## 2. Header de áreas y publicaciones (`header.category-pub-header`)

### Desktop — estado normal

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa + fixed items  │  logo + pill  │  search + login/susc│
│  link a home + nav de secciones del área o publicación              │
└─────────────────────────────────────────────────────────────────────┘
```

- `pill` es un identificador visual de la publicación/área; proviene de
  `utopia_cms_ladiaria` (bloque `header_pill`).
- El nav incluye un link a home de la publicación/área más las secciones.

### Desktop — sticky

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa  │  logo + pill  │  login/suscribir               │
└─────────────────────────────────────────────────────────────────────┘
```

### Mobile — estado normal

```
┌────────────────────────────────┐
│  menú hamburguesa │ logo + pill │        │
│  nav de secciones del área o publicación│
└────────────────────────────────┘
```

### Mobile — sticky

```
┌────────────────────────────────┐
│  menú hamburguesa │ logo + pill │        │
└────────────────────────────────┘
```

---

## 3. Header de artículo (`body.article`)

### Desktop — único estado (normal y sticky son visualmente iguales)

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa + breadcrumb  │  logo + pill  │  search + login/susc│
└─────────────────────────────────────────────────────────────────────┘
```

- El breadcrumb muestra área/publicación > sección.
- `pill` proviene de `utopia_cms_ladiaria`; puede estar ausente según la
  publicación.
- El sticky está activo pero no produce cambio visual.

### Mobile — estado normal

```
┌────────────────────────────────┐
│  menú hamburguesa │ logo │ search │
│         breadcrumb             │
└────────────────────────────────┘
```

### Mobile — sticky

```
┌────────────────────────────────┐
│  menú hamburguesa │ logo │ search │
└────────────────────────────────┘
```

- El breadcrumb desaparece al fijar el header.

---

## 4. Header por defecto (resto del sitio)

Aplica a todas las páginas que no son portada, área/publicación ni artículo
(suscripción, login, búsqueda, etc.).

### Desktop y Mobile — único estado (normal y sticky son visualmente iguales)

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa  │  logo  │  search + login/suscribir             │
└─────────────────────────────────────────────────────────────────────┘
```

- El sticky está activo pero no produce cambio visual.

---

## 5. Estado: menú extendido abierto (`body.main-menu-open`)

Aplica sobre cualquier tipo de header cuando el usuario abre el menú principal.

- El fondo del header cambia al color secundario (`$secondary-color`).
- El botón hamburguesa se reemplaza por el botón de cerrar (✕).
- El menú `.ld-main-menu` se despliega en pantalla completa debajo del header.
