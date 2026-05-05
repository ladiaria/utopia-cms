# Management Commands

## adzone

| Comando | Descripción |
|---------|-------------|
| `delete_old_impressions_and_clicks` | Elimina impresiones y clicks registrados hace más de 90 días. |
| `sync_new_impressions_and_clicks` | Elimina de MongoDB las impresiones y clicks nuevos e imprime el SQL para insertarlos en la DB relacional. |

## core

| Comando | Descripción |
|---------|-------------|
| `article_report` | Genera un CSV con datos de artículos publicados y lo escribe en stdout. |
| `download_section` | Descarga el HTML de una sección y lo guarda en `/tmp/<section>_<branch>.html`. |
| `dump_articles` | Exporta artículos (por ID o filtro) a un archivo JSON cargable con `loaddata`. También copia las imágenes relacionadas a un subdirectorio `photos`. |
| `generate_google_news_ai_feed` | Genera archivos RSS XML de Google News AI (uno por día) para transferencia trimestral a Google Drive. |
| `heavy_user_report` | Guarda en CSV los heavy users del mes actual y los tres meses anteriores. |
| `push_notification_stats` | Muestra estadísticas de push notifications desde logs y base de datos. |
| `section_update_category` | Cambia la categoría de una sección y actualiza las URLs de los artículos cuya sección principal sea la indicada. |
| `send_category_nl` | Envía el último newsletter de una categoría a todos sus suscriptores (o a los indicados por ID). |
| `send_command_testlog` | Prueba manualmente la salida y entradas de log generadas por `SendNLCommand`. |
| `send_notification` | Envía una push notification a los dispositivos suscritos de un usuario (por ID), o a todos si no se especifica usuario. |
| `sendnewsletter_delete_old_logs` | Agrupa archivos de log por patrón, los ordena por fecha y conserva solo los últimos N por grupo. |
| `sync_article_views` | Sincroniza las vistas de artículos y resetea los contadores en la tabla de caché. |
| `sync_articleviewedby` | Mueve los datos de "artículo visto por" de MongoDB al modelo Django. |
| `update_article_urls` | Actualiza (guarda) todos los artículos publicados como principales en las publicaciones indicadas por slug (o en todas). |
| `update_category_home` | Crea una tarea en background para la función `update_category_home`. |
| `utopiacms_process_tasks` | Wrapper de `process_tasks` que además maneja excepciones. |

## dashboard

| Comando | Descripción |
|---------|-------------|
| `activity` | Genera el contenido del reporte de actividad. |
| `activity_only_digital` | Genera el reporte de actividad solo para suscriptores digitales. |
| `article_views` | Genera el reporte de vistas de artículos ordenado por categoría o publicación. |
| `articles` | Genera y rota el reporte de artículos usando datos de MongoDB del último mes. |
| `audio_statistics` | Escribe estadísticas de audio en un CSV. |
| `categories` | Genera el reporte de artículos por categoría. |
| `content` | Genera un reporte de contenido con artículos y caracteres publicados por mes y sección. |
| `nldelivery_stats_from_log` | Obtiene (y opcionalmente actualiza) estadísticas de entrega de newsletters desde el archivo de log. |
| `nldelivery_sync_stats` | Actualiza las estadísticas de entrega de newsletters con datos de eventos de Google Analytics. |
| `sections` | Genera el reporte de artículos por sección. |
| `subscriber_data` | Genera un CSV con datos de todos los suscriptores. |
| `subscribers` | Genera el reporte de visitas de suscriptores. |

## homev3

| Comando | Descripción |
|---------|-------------|
| `download_home` | Descarga el HTML de la homepage y lo guarda en `/tmp/home_<branch>.html`. |

## notification

| Comando | Descripción |
|---------|-------------|
| `emit_notices` | Emite las notificaciones encoladas. |

## photologue_ladiaria

| Comando | Descripción |
|---------|-------------|
| `convert_photo_to_webp` | Convierte fotos a WebP. Acepta IDs individuales, un rango con `--from-id`/`--to-id`, o todas las fotos si no se especifica nada (pide confirmación salvo `--noinput`). |
| `utopiacms_photosizes` | Crea los photosizes necesarios para utopia-cms si no existen. |

## signupwall

| Comando | Descripción |
|---------|-------------|
| `signupwall_reset` | Resetea los contadores del signupwall (colecciones MongoDB). **Solo funciona con `DEBUG=True`.** |

## thedaily

| Comando | Descripción |
|---------|-------------|
| `mergedocs` | Unifica suscriptores y usuarios con el mismo número de documento. |
| `notifications_preview` | Genera una preview de notificaciones (uso en desarrollo/test). |
