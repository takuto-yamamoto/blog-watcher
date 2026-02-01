# ChangeDetector tests readability refactor plan

## Context
- Target: `tests/unit/detection/test_change_detector.py`
- Goal: improve readability without changing test intent (tests are spec).
- Current pain: tests require many URL mappings and low-level setup; intent gets buried.

## Problem decomposition
1) **Spec URLs vs implementation URLs are mixed**
   - Spec-relevant: base page, feed URL, robots.txt, sitemap URL.
   - Implementation detail: multiple feed fallbacks, sitemap_index.xml, etc.
   - Result: test body is noisy; important URLs are not visually salient.

2) **Test data setup is repetitive and procedural**
   - Repeated `FetchResultFactory.build(content=...)` with common fixtures.
   - Repeated `read_fixture(...)` and URL string assembly.
   - Fingerprint calculation in tests duplicates production logic.

3) **FakeFetcher is too low-level**
   - Every test must know the exact set of fetch calls.
   - Hard to express intent like "sitemap should not be accessed".

4) **ChangeDetector bundles multiple stages**
   - Feed detection, feed diff, robots/sitemap discovery, sitemap diff.
   - Tests behave like small integration tests; setup cost is high.

## Refactor strategy (non-breaking)
### A) Add test helpers/fixtures to express intent
- Introduce helper(s) in `tests/helpers/detection.py` or similar:
  - `build_fetcher_for_feed(blog, *, html=None, feed=None, robots=None, sitemap=None, fallbacks='strict')`
  - `build_state(blog, *, entry_keys=None, sitemap_fp=None)`
  - `assert_not_fetched(fetcher, "sitemap")`
- Add factories for common fixtures:
  - `feed_link_html()` -> `FetchResultFactory.build(content=read_fixture("html/feed_link_rss.html"))`
  - `rss_valid()` -> `FetchResultFactory.build(content=read_fixture("feeds/rss_valid.xml"))`
  - `sitemap_urlset()` -> `FetchResultFactory.build(content=read_fixture("sitemap/urlset.xml"))`

### B) Encode URL conventions centrally
- Add a small URL helper:
  - `blog_urls(blog)` returns base, feed, robots, sitemap.
- Use it in tests to reduce literal strings and highlight intent.

### C) Hide fallback noise in helper
- For tests that don’t care about fallback probing, let helper auto-register
  default fallback paths (or ignore them) so the test doesn’t list them all.
- Provide two modes:
  - `strict=True`: undefined URL access is error (good for tests asserting "not fetched").
  - `permissive=True`: undefined URL access returns empty content (good for fallback-heavy tests).

### D) Remove production logic from tests
- Avoid computing `fingerprint_urls(normalize_urls(...))` in tests.
- Replace with a canned fingerprint value or a helper that names intent:
  - `sitemap_fp_for_example_site()` returning a stable string.

## Proposed file structure
- `tests/helpers/detection.py`
- `tests/helpers/__init__.py`
- (Optional) `tests/fixtures/detection.py` for shared fixtures

## Example before/after (conceptual)
### Before
- Test includes 10+ URLs in dict, multiple `read_fixture`, and fingerprint logic.

### After
- Test body focuses on intent:
  - "feed unchanged" + "sitemap fingerprint changed" => changed=True.
  - Uses `build_fetcher_for_feed(...)`, `build_state(...)`.

## Optional design-level improvement (longer term)
- Split ChangeDetector into smaller collaborators:
  - `FeedChangeDetector`
  - `SitemapChangeDetector`
- Keep current tests as integration-level, but add focused unit tests per stage.

## Acceptance criteria
- Test bodies are <20 lines on average.
- No test includes direct normalization/fingerprint computation.
- URL lists appear only in helpers, not inline tests.
- Assertions read like spec sentences.

## Next steps
1) Create helper module(s) and migrate one test as exemplar.
2) Migrate remaining tests incrementally.
3) Re-evaluate whether ChangeDetector should be decomposed after readability improves.
