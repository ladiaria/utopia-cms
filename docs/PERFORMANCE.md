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
- The computed list of edition IDs is now stored in the Django cache under the key
  `get_current_feeds_edition_ids` with a 300-second TTL. Subsequent requests within that window
  skip the publication loop entirely.
- The returned queryset now chains `.select_related('photo', 'photo__extended',
  'photo__extended__photographer').prefetch_related('byline', 'sections')`, eliminating the N+1
  per article for photos, authors, and sections.

#### `urls.py` — `feeds/articulos/` URL
- Wrapped `LatestArticles()` with `cache_page(300)` so the full rendered XML response is cached
  for 5 minutes. Requests within that window return immediately without hitting the
  database at all.
- `cache_page` import added alongside the other `django.views` imports.

### Expected impact
- Cold request (cache miss): query count drops from ~2N+3+90–120 to ~2N+3+3 (select + 2 prefetch
  JOINs). Typical time should fall well under 1 second.
- Warm request (cache hit on `cache_page`): <10 ms, served entirely from cache.

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
  cache under `masleidos_full_content` with a 600-second TTL (same as the previous
  `@cache_page` TTL). On cache hit the three SQL queries are skipped entirely.
- `index` now calls `_get_full_content_ids()` directly instead of calling the view function.
- `mas_leidos_fullcontent` (the JSON endpoint) also delegates to `_get_full_content_ids()`, so
  both endpoints share the same cached data and the queries run at most once per 10 minutes.
- Removed orphaned `from json import loads` import.

### Expected impact
- Cold request (cache miss): three SQL queries run once, result cached for 10 minutes.
- Warm request (cache hit): zero SQL queries, data served from cache.
- Cache stampede eliminated: concurrent requests all hit the same cache key.

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

### Async comment count via Django proxy
Coral's GraphQL API blocks direct queries from client JS (`RAW_QUERY_NOT_AUTHORIZED`), even with
the user auth token. A thin Django proxy endpoint was added instead:

- **`GET /articulo/<id>/comment-count/`** (`coral_comment_count` view in `core/views/article.py`)
  calls Coral's GraphQL API server-side using `TALK_API_TOKEN`, caches the result
  under `coral_comment_count_<id>` with a 120-second TTL, and returns `{"count": N}`.
- On failure, retries up to 2 times with exponential backoff (0.5s, 1s) before returning 0.
- A `fetchCommentCount()` IIFE in `static/js/ld.js` calls this endpoint after page load and
  updates the comments button and section header with the real count. The page renders
  immediately with "Comentar" as fallback; the count appears asynchronously once the fetch
  resolves.

---

## `/masleidos/` — N+1 queries on every authenticated request

**Date:** 2026-05-28
**Branch:** `perf/masleidos-select-related`

### Root cause identified

`get_articles_by_ids()` (`core/views/masleidos.py`) fetched articles with a plain
`Article.objects.filter(id__in=ids)` — no `select_related`, no `prefetch_related`.
The template `media-list.html` then accessed two relationships per article that Django
resolved with individual lazy queries:

- **`article.publication_section()`** walks `main_section → edition → publication` (two FK
  hops). Without `select_related`, each hop is a separate query.
- **`article.get_authors()`** calls `self.byline.all()` — a M2M relation that fires one query
  per article without `prefetch_related`.

`/masleidos/` renders three tabs (daily, weekly, monthly) of 10 articles each — 30 articles
total. At 3 lazy queries per article that is **~90 extra queries per request**.

The `@cache_page` decorator on `index` does not cache requests from authenticated users
(Django skips page caching when session cookies are present). Since most `/masleidos/` visitors
are logged-in subscribers, the N+1 hit affected the vast majority of real traffic. The problem
was identified via uwsgi log analysis: `/masleidos/` appeared consistently at **avg 1.9s, max
5.5s** across the 7 peak-hour log files from 2026-05-28 (07:00–10:00 AM), despite the cache
fix applied on 2026-05-26 which only eliminated the SQL aggregation stampede.

### Fix applied

#### `core/views/masleidos.py` — `get_articles_by_ids()`

```python
# Before
articles_by_id = {a.id: a for a in Article.objects.filter(id__in=ids)}

# After
qs = Article.objects.filter(id__in=ids).select_related(
    'main_section__edition__publication',
    'main_section__section__category',
).prefetch_related('byline')
articles_by_id = {a.id: a for a in qs}
```

- `select_related('main_section__edition__publication', 'main_section__section__category')`:
  fetches the full FK chain used by `publication_section()` in a single JOIN, covering both
  the publication lookup and the category lookup needed by `render_hierarchy`.
- `prefetch_related('byline')`: resolves the author M2M in one batched query for all articles,
  instead of one query per article.

`get_articles_by_ids()` is only called from two places, both in the same file: `index` (the
three-tab page) and `content` (the sidebar widget on the homepage). Both benefit from the fix.

### Expected impact

- Query count per request: ~90 lazy queries → **3 fixed queries** (1 filtered SELECT with JOINs
  + 1 prefetch for byline + the raw SQL aggregation from `_get_full_content_ids()`), regardless
  of how many articles are displayed.
- The improvement is only visible for **authenticated users** — anonymous requests were already
  served by `@cache_page`.

### How to verify locally

The easiest way is Django's built-in query logging. Add this to `local_settings.py` temporarily:

```python
LOGGING = {
    'version': 1,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django.db.backends': {'handlers': ['console'], 'level': 'DEBUG'},
    },
}
```

Start the dev server, log in as a subscriber, and open `/masleidos/`. Count the queries in the
terminal output. Before this fix: ~90+ queries. After: 3.

Alternatively, set `DEBUG_TOOLBAR_ENABLE = True` in `local_settings.py` (requires
`pip install django-debug-toolbar`) and use the SQL panel — the project already has the
configuration wired up.
