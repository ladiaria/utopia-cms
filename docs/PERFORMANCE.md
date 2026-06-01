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

---

## `/masleidos/` — context processors re-executing per article (464 → 30 queries)

**Date:** 2026-05-28
**Branch:** `perf/masleidos-select-related`

### Root cause identified

`RenderArticleMediaNode.render()` (`core/templatetags/core_tags.py`) called
`loader.render_to_string('media-list.html', context=context.flatten(), request=context.request)`.

Passing `request` to `render_to_string` tells Django to run the full context processor pipeline
for that render. With 31 articles across the three tabs, every registered context processor ran
31 times — including ones that hit the database:

- `context_processors.site` — 2 queries for robots rules (`robots_rule` + `robots_url`)
- `context_processors.publications` — 1 query (`Publication.objects.get`)
- `context_processors.main_menus` — 1 query (`Category.objects.filter`)
- `utopia_cms_ladiaria.context_processors.ladiaria` — 2 queries (tag lookup + article by tag)
- `utopia_cms_liveblog.context_processors.liveblog` — 1 query (`LiveBlog.objects.filter`)

That is ~7 queries × 31 articles = **~217 extra queries per request**, on top of the N+1 from
`get_articles_by_ids()`.

### Fix applied

#### `core/templatetags/core_tags.py` — `RenderArticleMediaNode.render()`

Removed `request=context.request` from the `render_to_string` call. `context.flatten()` already
contains all context processor output from the parent request — there is no need to re-run them
for each sub-template render. The `user` variable (needed by `media-list.html` for the read-later
button) comes through `context.flatten()` and remains available.

```python
# Before
return loader.render_to_string(
    'core/templates/article/media-list.html', context=context.flatten(), request=context.request
)

# After
return loader.render_to_string(
    'core/templates/article/media-list.html', context=context.flatten()
)
```

### Expected impact

- Context processor queries eliminated: ~217 queries (7 per article × 31 articles) → 0.
- Combined with the `select_related`/`prefetch_related` fix and the `follows` precomputation,
  total query count for `/masleidos/` dropped from **464 to ~30** for authenticated users.

### Why context processors run on `render_to_string`

Django only runs context processors when a `RequestContext` is active. Passing `request` to
`render_to_string` implicitly creates a `RequestContext`, which triggers the full processor list.
Passing only a plain dict (or a pre-flattened context) skips them entirely.

Any `render_to_string(..., request=request)` call inside a template loop is a potential N+1
source if any context processor does database work. The pattern to watch for: a template tag
that renders a sub-template in a loop and passes `request`.

### Bonus fix: `object_id` type mismatch in follows list

`actstream` stores `object_id` as a `CharField`. `values_list('object_id', flat=True)` returns
strings, so `{% if a.id in follows %}` in the template silently failed — `109648 in ['109648']`
is `False` in Python. Fixed by casting to `int` when building the list in `index()`:

```python
follows = [
    int(oid) for oid in user.follow_set.filter(...).values_list('object_id', flat=True)
]
```

### If this pattern reappears elsewhere

Do **not** add per-request caching (`request._ctx_*`) to context processors as a workaround —
it couples unrelated code and is easy to get wrong if a context processor result depends on the
specific view. The correct fix is always to avoid passing `request` to sub-template renders
inside loops, since the parent context already contains the processor output.

---

## `usuarios/lista-lectura-leer-despues/` and `usuarios/lista-lectura-historial/` — N+1 queries

**Date:** 2026-05-28
**Branch:** `perf/lista-lectura-queries`

### Root causes identified

Both views had two problems:

#### 1. `follows` not passed to template context
Both views rendered `lista-lectura.html` which includes `article_card_read_later.html` with
`prefetched_article_data=True` but without a `follows` list. This caused the template to fall
through to the `{% elif not a.is_restricted or user|has_restricted_access:a %}` branch, which
calls `{% if user|is_following:a %}` — one actstream query per article.

#### 2. No `select_related`/`prefetch_related` on article objects
Articles came from `recent_following()` and `user_read_history()` as plain objects with no
prefetching, causing N+1 queries in the template for `article.get_authors()` and
`article.main_section`.

### Fixes applied

#### `thedaily/views.py` — `lista_lectura_leer_despues()`
- After pagination, re-fetches the page's articles via `Article.objects.filter(id__in=page_ids)`
  with `select_related` and `prefetch_related('byline')` to eliminate template N+1.
- Passes `follows=page_ids` (all articles on this page are already followed by the user by
  definition) and `prefetched_article_data=True` to skip the per-article `is_following` call.

#### `thedaily/views.py` — `lista_lectura_historial()`
- Same re-fetch pattern after pagination.
- Passes `follows` computed with a single scoped `follow_set` query over the page's article IDs,
  cast to `int` (actstream `object_id` is a `CharField`).
- Passes `prefetched_article_data=True`.

### Regression introduced by this branch (fixed 2026-06-01)

The `page_ids = [a.id for a in followings.object_list]` line added to `lista_lectura_leer_despues()`
above raised `'NoneType' object has no attribute 'id'` for any user with a **deleted** followed
article: `recent_following()` returned `follow.follow_object`, which actstream resolves to `None`
when the object is gone. The previous code never dereferenced `.id`, so the bad data was latent and
harmless until this refactor. Fixed by dropping the `None` entries in `recent_following()` itself
(also corrects a slightly inflated read-later count). Regression test:
`thedaily/tests/test_recent_following.py`.

### Remaining known N+1 (not fixed in this branch)

Both utility functions that build the full article list before pagination still have an
unavoidable N+1:

- **`recent_following()`** (`thedaily/utils.py:155`): `fetch_generic_relations` from actstream
  calls `get_object_for_this_type(pk=pk_val)` per follow — one `Article.objects.get` per item.
- **`user_read_history()`** (`thedaily/utils.py:278`): calls `Article.objects.get(id=article_id)`
  inside a loop over MongoDB results.

These fire before pagination, so they scale with the user's total follow/history count, not the
page size. Fixing them requires refactoring both functions to fetch all article IDs first and
resolve objects in a single batch query. That work is left for a future branch.

---

## `usuarios/lista-lectura-historial/` — unbounded N+1 before pagination (avg 6s, max 20s)

**Date:** 2026-06-01
**Branch:** `perf/lista-lectura-historial-n1`

### Root cause identified

The 2026-05-28 branch added `select_related`/`prefetch_related` for the **displayed page** of
`lista_lectura_historial()`, but the line above it still called `user_read_history(request.user)`
with **no `limit`**. That builds the user's *entire* read history before paginating, and
`user_read_history()` (`thedaily/utils.py`) resolves every item with an individual
`Article.objects.get(id=article_id)` inside the MongoDB loop plus an unprefetched walk over the
relational `articleviewedby_set`. A user with thousands of viewed articles triggers thousands of
queries just to `len()` the list and show 10 rows.

This was the worst endpoint in the 2026-06-01 (06:13–10:13) peak log analysis: **avg 5973ms, max
19676ms**, scaling directly with history size (53ms for a small history → ~20s for a large one).
It was the top source of the 181 HTTP 499 (client-aborted) responses that morning. The
2026-05-28 branch had documented this exact case as "left for a future branch" (see section
above).

### Data model context (Mongo ↔ Postgres)

Read history lives in two places. Authenticated article views are upserted into MongoDB
(`core_articleviewedby`, in `core/views/article.py`) as a hot write buffer. The
`sync_articleviewedby` management command drains Mongo with `find_one_and_delete` and consolidates
each doc into the relational `ArticleViewedBy` model. So **Mongo = recently viewed / not yet
synced; Postgres = consolidated history**. `user_read_history()` unions the two (Mongo first,
newest, then Postgres excluding ids already seen in Mongo).

### Fix applied

#### `thedaily/utils.py` — `user_read_history(..., ids_only=False)`

Added an `ids_only` fast path that returns ordered `(article_id, viewed_at)` tuples **without
instantiating any `Article`**: the Mongo cursor contributes its ids directly, and the relational
union uses `values_list('article_id', 'viewed_at')` instead of touching `avb.article`. Removed
articles are no longer filtered here — a stale id is dropped naturally by the caller's batched
`Article.objects.filter(id__in=...)`. The original (object-returning) behaviour is untouched, so
the other two callers (`last_read` with `limit=5`, `read_articles_percentage` with
`mongo_db_only=True`) are unaffected.

#### `thedaily/views.py` — `lista_lectura_historial()`

Now calls `user_read_history(request.user, ids_only=True)`, paginates over the id tuples, and
materializes **only the page's 10 articles** with the existing `select_related`/`prefetch_related`
query. `historial_count` comes from `len()` of the cheap id list.

### Expected impact

- Query count per request: **~N (history size)** → **fixed (~20 for a 10-item page)**, independent
  of history size.
- The 17–20s outliers should disappear; the 499s caused by users abandoning the slow page should
  go with them.

### Measured locally (debug toolbar, user with 501-item history)

| | main (before) | branch (after) |
|---|---|---|
| SQL queries | **521** | **20** |
| SQL time | 920 ms | 19.5 ms |
| CPU time | 4049 ms | 232 ms |

The 521 → 20 drop is exactly one `Article.objects.get()` per history item eliminated. The query
count on the branch is fixed by page size (10), not by total history size.

### `recent_following()` still pending

`recent_following()` (`thedaily/utils.py`) has the same actstream-driven N+1, but
`/lista-lectura-leer-despues/` measured fast in the 2026-06-01 peak (avg 112ms) because users
follow few articles. Same `ids_only`-style refactor applies if it ever shows up in the logs.
