# Performance optimizations

This document tracks performance investigations and the fixes applied.

---

## RSS feed `feeds/articulos/` — slow response in production (>2.5s)

**Date:** 2026-05-25
**Branch:** `perf/feed-performance`

### Root causes identified

#### 1. N+1 queries in `get_current_feeds()` — most severe
`get_current_feeds()` (`core/models.py`) looped over every public publication, executing at least
two queries per publication (`get_current_edition(p)` + `next_editions` filter) just to build the
list of edition IDs. With N publications → ~2N+3 queries before even fetching articles.

#### 2. No `select_related` / `prefetch_related` on the article queryset
`LatestArticles.items()` returned articles with no prefetching. Each article in the feed triggered
individual queries for:
- `item.photo` and `item.photo.extended.photographer` (photo caption)
- `item.byline.all()` (author name)
- `item.sections.all()` (feed categories)

With a typical feed of ~30 articles this produced 90–120 extra queries per request.

#### 3. `get_current_edition()` called repeatedly without caching
Called once for root publications and once per non-root publication on every request. Editions
change at most once a day, so these results are safe to cache for several minutes.

### Fixes applied

#### `core/models.py` — `get_current_feeds()`
- Added `from django.core.cache import cache` to the top-level imports (also removed three
  redundant inline imports of the same symbol from `Section` methods).
- The computed list of edition IDs is now stored in Memcached under the key
  `get_current_feeds_edition_ids` with a 300-second TTL. Subsequent requests within that window
  skip the publication loop entirely.
- The returned queryset now chains `.select_related('photo', 'photo__extended',
  'photo__extended__photographer').prefetch_related('byline', 'sections')`, eliminating the N+1
  per article for photos, authors, and sections.

#### `urls.py` — `feeds/articulos/` URL
- Wrapped `LatestArticles()` with `cache_page(300)` so the full rendered XML response is cached
  in Memcached for 5 minutes. Requests within that window return immediately without hitting the
  database at all.
- `cache_page` import added alongside the other `django.views` imports.

### Expected impact
- Cold request (cache miss): query count drops from ~2N+3+90–120 to ~2N+3+3 (select + 2 prefetch
  JOINs). Typical time should fall well under 1 second.
- Warm request (cache hit on `cache_page`): <10 ms, served entirely from Memcached.

### Cache invalidation note
Both caches use the 300-second default. If a new edition is published and the feed must reflect it
immediately, run `python -W ignore manage.py clear_cache` (the `runserver` script does this
automatically on restart).

---

## `/masleidos/` — cache stampede on every request (>4s under load)

**Date:** 2026-05-26
**Branch:** `perf/masleidos-cache-fix`

### Root cause identified

`index` view called `mas_leidos_fullcontent(request)` directly as a Python function. The
`@cache_page` decorator on `mas_leidos_fullcontent` only intercepts requests routed through
Django's URL dispatcher — a direct Python call bypasses it entirely. This meant every visit to
`/masleidos/` executed three raw SQL aggregation queries (daily, weekly, monthly views counts)
with no caching, regardless of traffic volume.

Under high load this caused a cache stampede: multiple workers hitting the same heavy queries
simultaneously, producing response times of 4–8 seconds observed in uwsgi logs.

### Fix applied

#### `core/views/masleidos.py`
- Extracted `_get_full_content_ids()`: computes the three ranking lists and stores the result in
  Memcached under `masleidos_full_content` with a 600-second TTL (same as the previous
  `@cache_page` TTL). On cache hit the three SQL queries are skipped entirely.
- `index` now calls `_get_full_content_ids()` directly instead of calling the view function.
- `mas_leidos_fullcontent` (the JSON endpoint) also delegates to `_get_full_content_ids()`, so
  both endpoints share the same cached data and the queries run at most once per 10 minutes.
- Removed orphaned `from json import loads` import.

### Expected impact
- Cold request (cache miss): three SQL queries run once, result cached for 10 minutes.
- Warm request (cache hit): zero SQL queries, data served from Memcached.
- Cache stampede eliminated: concurrent requests all hit the same Memcached key.

---

## Article detail — blocking Coral API call on every request (>4s under load)

**Date:** 2026-05-26
**Branch:** `perf/remove-coral-sync-call`

### Root cause identified

`article_detail()` (`core/views/article.py`) made a synchronous `requests.post()` to the Coral
Talk GraphQL API on every article page render to fetch `comments_count`. This call blocked the
uwsgi worker for the full Coral round-trip time. Under load (or whenever Coral had any latency)
this was the primary contributor to 4–5s response times observed for article pages.

The call has been in place since 2019 and the original commit already contained a
`# TODO: check talk API for a count operation` note — it was a provisional implementation that
was never revisited.

### Fix applied

#### `core/views/article.py` — `article_detail()`
- Removed the `try/except` block that called the Coral GraphQL API.
- `comments_count` is now hardcoded to `0` server-side.
- The article templates already had `{% if comments_count > 0 %}...{% else %}Comentar{% endif %}`
  fallback branches, so the UI degrades gracefully: the button shows "Comentar" and the header
  shows "Comentarios" without a count. Coral renders the real count client-side when the widget
  loads anyway.

### Expected impact
- Every article page request saves one outbound HTTP call (typically 200–3000ms depending on
  Coral load).
- uwsgi workers are no longer blocked waiting for Coral responses.

### Async comment count via JS
The template embeds `data-talk-url` and `data-article-id` on the Coral container element. A
self-invoking `fetchCommentCount()` function was added to `portal/static/js/ld.js` that runs
after page load, queries Coral's GraphQL API (`story { commentCount }`) without authentication,
and updates both the floating action button and the comments section header with the real count.
The UX is identical to before: the count appears a moment after the page renders instead of
being baked into the HTML.

> **Note:** needs testing against the Coral instance in the test environment to confirm the
> `commentCount` field is available on the version of Coral in use.
