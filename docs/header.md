# Header — tipos y comportamientos

El header está implementado principalmente en `utopia-cms`. Algunos elementos
(`fixed items`, `header-pill`) viven en la app externa `utopia_cms_ladiaria`
y se inyectan vía bloques de template.

El componente base es `portal/templates/header.html`.
Los estilos están en `static/sass/utopia_header.scss`.

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
│  menú hamburguesa + fixed items  │        │  search + login/suscribir│
│                                  │  logo  │                          │
│           nav de áreas y publicaciones                               │
└─────────────────────────────────────────────────────────────────────┘
```

- El logo ocupa la fila central en solitario.
- `fixed items` proviene de `utopia_cms_ladiaria`.

### Desktop — sticky (al hacer scroll)

```
┌─────────────────────────────────────────────────────────────────────┐
│  menú hamburguesa  │  logo  │  search + login/suscribir             │
└─────────────────────────────────────────────────────────────────────┘
```

- Colapsa a una sola fila.
- Desaparece el nav de áreas/publicaciones y los fixed items.

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
│  menú hamburguesa + fixed items  │             │  search + login/susc│
│                                  │  logo + pill│                     │
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

---

## Deuda técnica: transición brusca al hacer scroll en la portada

### Problema

Afecta a la **portada** (`header.home-header`) y al **header de áreas y
publicaciones** (`header.category-pub-header`): ambos tienen estado normal de
3 filas y estado sticky de 1 fila, y el cambio es abrupto porque la
implementación usa **dos nodos DOM distintos para el logo** y alterna el layout
completo entre ellos:

- **Estado normal**: `.logo-desktop-container` (logo grande, fila central)
  está visible; `.upper-center-logo-container` está oculto (`display: none`).
- **Estado sticky**: `.logo-desktop-container` pasa a `display: none`;
  `.upper-center-logo-container` aparece en la columna central de la fila
  superior.

Como se intercambian con `display: none/flex`, no hay nada que CSS pueda
animar entre los dos estados.

### Solución propuesta

Refactor acotado que toca `header.html` y `utopia_header.scss`:

1. **Eliminar `.logo-desktop-container`** del template. Queda un único logo:
   el de `.upper-center-logo-container`, visible siempre.

2. **En estado normal del home**, el logo se ve grande y centrado mediante CSS,
   no por estar en una fila separada:
   - `.upper-content` tiene más `padding-block`.
   - El logo tiene `max-width` mayor (ej: 180px).

3. **Al agregar `.sticky`**, en vez de intercambiar nodos, se transiciona:
   - `max-width` del logo: 180px → 108px.
   - `padding-block` de `.upper-content`: colapsa.
   - `max-height` del nav: colapsa a 0.

4. El JS que agrega la clase `.sticky` no necesita cambios.
