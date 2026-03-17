# photologue_ladiaria – WebP y última subida original

Esta app extiende Photologue para:

- **Recorte para una posible versión "cuadrada" de la foto**: se puede generar una versión cuadrada de la foto y se guarda en `PhotoExtended.square_version`. TODO: ampliar este punto.
- **Conversión automática a WebP**: si `PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP` está en `True` (por defecto), al guardar una foto su imagen se convierte a WebP (se reemplaza el archivo en `photo.image`).
- **Última subida original** (`last_original_uploaded` en `PhotoExtended`): se guarda una copia del archivo tal como se subió la última vez (JPG, PNG o WebP), para poder ofrecer descargas en formato original, etc.

El comportamiento se define por **cómo se detecta si la imagen fue reemplazada o no** en cada save. Para eso se usa un `pre_save` en `Photo` que guarda en la instancia:

- `_previous_image_name`: path/nombre del `image` en la DB antes del save.
- `_previous_image_hash`: hash MD5 del contenido del archivo anterior (para detectar mismo nombre pero distinto contenido).

En el `post_save` se llama a `convert_to_webp`, que decide si convierte, si actualiza `last_original_uploaded` o si no toca archivos.


## Casos y resolución de la conversión a WebP

### 1. Plain save (guardar sin cambiar la imagen)

**Qué es:** El usuario solo cambia otros campos (título, caption, etc.) y guarda. No sube ni reemplaza el archivo de la imagen.

**Detección:** En `pre_save` tenemos el nombre anterior del `image`. Tras el save, `photo.image.name` es el mismo → **nombre no cambió**. El hash del contenido anterior coincide con el actual (mismo archivo) o no se usa el fallback (p. ej. `last_original` es JPG y la imagen actual es WebP).

**Qué hacemos:** No se toca ningún archivo. `last_original_uploaded` no se modifica.

---

### 2. Nueva foto (create)

**Qué es:** Se crea una `Photo` con una imagen subida (JPG, PNG o WebP).

**Detección:** No hay `pk` → `_previous_image_name` y `_previous_image_hash` son `None` → se considera “imagen nueva”.

**Qué hacemos:**

- Si el archivo **no es WebP** (p. ej. JPG/PNG): se guarda una copia en `last_original_uploaded`, se convierte a WebP y se reemplaza `photo.image` por el WebP. Un segundo `post_save` se dispara al guardar el WebP; se evita sobrescribir `last_original` con ese WebP usando el flag `_webp_just_converted`.
- Si el archivo **ya es WebP**: no hay conversión; se actualiza `last_original_uploaded` con ese WebP (mismo contenido que la imagen actual).

---

### 3. Reemplazo por un archivo nuevo (nombre distinto)

**Qué es:** El usuario sube otra imagen (JPG, PNG o WebP) y el storage asigna un path/nombre distinto al anterior.

**Detección:** `photo.image.name != _previous_image_name`.

**Qué hacemos:**

- Si el archivo **no es WebP**: se guarda una copia en `last_original_uploaded`, se convierte a WebP y se actualiza `photo.image`. No se pisa `last_original` en la reentrada por el flag `_webp_just_converted`.
- Si el archivo **ya es WebP**: se actualiza `last_original_uploaded` con ese WebP (mismo archivo que la imagen actual).

---

### 4. Reemplazo por un archivo con el mismo nombre pero distinto contenido

**Qué es:** El usuario sube otro archivo (p. ej. otro WebP) que el storage guarda con el mismo path/nombre que antes (mismo nombre de archivo, contenido distinto).

**Detección:**

- **Con hash:** En `pre_save` se leyó el archivo anterior y se guardó `_previous_image_hash`. En `post_save` se calcula el hash del contenido actual. Si `photo.image.name` no cambió pero `hash(contenido_actual) != _previous_image_hash` → **mismo nombre, distinto contenido**.
- **Fallback (sin hash):** Si no hay `_previous_image_hash` (p. ej. falló la lectura en `pre_save`), se compara el contenido actual con el de `last_original_uploaded`. Solo si **ambos son WebP** (por magic bytes) y el contenido es distinto, se considera reemplazo. Así se evita marcar como reemplazo un plain save donde `last_original` es JPG y la imagen actual es WebP.

**Qué hacemos:** Se actualiza `last_original_uploaded` con el contenido actual (el nuevo WebP o el nuevo original antes de convertir). Si además el archivo no era WebP, se hace la conversión a WebP como en el caso 3.

---

### 5. Reemplazo por el mismo contenido (mismo nombre y mismo contenido)

**Qué es:** En la práctica, mismo archivo o contenido idéntico; el path puede ser el mismo o no.

**Detección:** Se considera “imagen reemplazada” por nombre o por hash, pero al escribir en `last_original_uploaded` se comprueba `_last_original_has_same_content(ext, content)`. Si el contenido ya es el mismo, no se escribe de nuevo.

**Qué hacemos:** No se sobrescribe `last_original_uploaded` (evitamos I/O y duplicados innecesarios).

---

## Resumen por tipo de save

| Situación                         | ¿Se convierte a WebP? | ¿Se actualiza last_original? |
|----------------------------------|------------------------|------------------------------|
| Plain save (solo otros campos)   | No                     | No                           |
| Nueva foto, archivo JPG/PNG      | Sí                     | Sí (copia del original)      |
| Nueva foto, archivo WebP         | No                     | Sí (copia del WebP)          |
| Nueva imagen, path distinto      | Sí si no es WebP       | Sí                           |
| Mismo path, contenido distinto   | Sí si no es WebP       | Sí (hash o fallback WebP)    |
| Mismo contenido ya en last_original | Según formato       | No (no se reescribe)          |

---

## Notas

- **Reentrada tras JPG→WebP:** Tras convertir y hacer `photo.save(update_fields=['image'])`, se pone `photo._webp_just_converted = True`. En la siguiente ejecución de `convert_to_webp` (mismo request), si la imagen ya es WebP y el flag está puesto, no se actualiza `last_original_uploaded` y se borra el flag. Así no se pisa el JPG recién guardado con el WebP.
- **Duplicado al subir WebP:** Si el usuario sube un WebP, se guarda una copia en `last_original_uploaded` (no se reutiliza el mismo archivo que `photo.image`). Se acepta ese duplicado para no complicar el ciclo de vida del archivo.
- **Setting:** `PHOTOLOGUE_LADIARIA_AUTO_CONVERT_TO_WEBP` (por defecto `True`) activa o desactiva la conversión automática; no afecta al guardado de `last_original_uploaded` cuando la conversión está activa.
