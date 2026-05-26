# Performance optimizations

This document tracks performance investigations and the fixes applied.

---

## RSS feed `feeds/articulos/` — slow response in production (>2.5s)

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
