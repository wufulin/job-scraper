# Learnings

## 2026-02-10 Pre-Planning (Metis Analysis)

### API Verification Results
- RemoteOK: Public JSON API at `/api` confirmed. First array element is a LEGAL NOTICE, not a job — must skip.
- 电鸭: Public API at `svc.eleduck.com/api/v1/posts?category=5` confirmed. No auth needed.
- WeWorkRemotely: RSS URL CHANGED — use `/remote-jobs.rss`, NOT `/categories/remote-programming-jobs.rss`
- V2EX: HTML list + API detail confirmed. Rate limit: 600 req/hour (headers: `x-rate-limit-limit: 600`)
- Arc.dev: Confirmed Next.js SPA. Selectors are TBD — needs live investigation in Phase 2.
- 远程.work: Shows "0 positions, 0 users" but has listings. Possibly unreliable.
- OfferShow: Could not load — likely behind Cloudflare. SKIP entirely.

### Tech Stack Gotchas
- httpx AsyncClient: Must use single long-lived client, not per-request
- Pydantic v2 HttpUrl: Cannot store directly in SQLite — needs `str(url)` serialization
- feedparser: `bozo_exception` silently set on parse errors; needs `chardet` for Chinese encoding
- SQLite + asyncio: Standard `sqlite3` blocks event loop — need `aiosqlite` (Phase 2 concern)
- Playwright: Memory leaks from unclosed pages/contexts (Phase 2 concern)

### Keyword Matching Gotchas
- `\bAI\b` regex works for English but NOT for Chinese text (no word boundaries)
- "AI应用" needs substring match, "email"/"wait" need word-boundary exclusion
- Solution: word-boundary regex for English, substring for CJK

### Architecture Decisions
- Phase 1 is SYNCHRONOUS (httpx sync mode). Async deferred to Phase 2.
- Phase 1 targets 3 easiest sources: RemoteOK API, 电鸭 API, WWR RSS
- OfferShow excluded from ALL phases
- Tests ship with the code they test, not deferred to Phase 4
- Python 3.11+ target (Pydantic v2, built-in generics)

## Task 1: Project Skeleton Setup (Completed)

### Files Created
- `pyproject.toml`: Setuptools-based config with Python >=3.11, all required dependencies
- Directory structure: `scraper/`, `scraper/adapters/`, `scraper/utils/`, `config/`, `data/`, `logs/`, `tests/`, `tests/test_adapters/`, `tests/fixtures/`
- All `__init__.py` files (empty, as per Python best practices)
- `.gitignore`: Comprehensive exclusions for data/, logs/, venv/, etc.
- `.env.example`: Placeholder config for PROXY_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LOG_LEVEL
- `config/sites.yaml`: 3 Phase 1 sites (RemoteOK, 电鸭, WeWorkRemotely) with correct endpoints
- `config/keywords.yaml`: Location and technology keyword groups with match rules
- `scraper/logger.py`: Loguru setup with daily rotation, 30-day retention, UTF-8 encoding

### Configuration Details
**sites.yaml structure:**
- RemoteOK: API adapter, skip_location_match=true
- 电鸭 (eleduck): API adapter with category=5 param
- WeWorkRemotely: RSS adapter, skip_location_match=true
- All sites have rate_limit_seconds=2 and User-Agent headers

**keywords.yaml structure:**
- Location keywords: remote, 远程, work from home, etc. (9 terms)
- Technology keywords: AI, LLM, machine learning, etc. (19 terms)
- Match rules: default "location AND technology", skip location for remoteok/weworkremotely

### Dependencies
Core: httpx, beautifulsoup4, feedparser, fake-useragent, pyyaml, loguru, pydantic>=2.0, chardet
Dev: pytest

### Logger Configuration
- Console output: INFO level by default (DEBUG if verbose=True)
- File output: logs/scraper_{time:YYYY-MM-DD}.log
- Rotation: Daily at midnight
- Retention: 30 days
- Encoding: UTF-8
- Function: `setup_logger(verbose=False)` returns configured logger

### Validation
- YAML files are syntactically valid (verified by manual inspection)
- Directory structure complete
- All required files present
- pyproject.toml follows setuptools backend specification

## Models Implementation

### Completed
- Created scraper/models.py with JobPosting Pydantic model
- All Phase 1 fields implemented: id, title, company, url, source, published_at, salary, location, description, tags, first_seen, last_seen, last_updated, update_count
- Field validators: title (strip whitespace, non-empty), source (must be in valid set)
- generate_id() static method using MD5 hash of url|title
- to_db_dict() serialization: datetime -> ISO string, list -> JSON string
- from_db_row() deserialization: ISO string -> datetime, JSON string -> list
- Used str for url field (NOT HttpUrl) for SQLite compatibility

### Verified
- Import works successfully
- Round-trip serialization/deserialization preserves all fields
- None values handled correctly
- Validators reject invalid inputs (empty title, invalid source)
- generate_id() produces consistent hashes for same inputs

### Key Decisions
- Used str for url instead of HttpUrl to avoid SQLite serialization issues
- Used json.dumps/loads for list serialization (tags field)
- Handled None datetime values gracefully (None -> None, not 'None')
- Pydantic v2 syntax with field_validator decorator


## Task 3: Keyword Matcher Implementation (Completed)

### Files Created
- `scraper/utils/matcher.py`: KeywordMatcher class with smart boundary detection
- `tests/test_matcher.py`: 32 comprehensive test cases covering all scenarios

### Implementation Details

**KeywordMatcher class:**
- `__init__(config=None, config_path=None)`: Loads config from dict or yaml file (defaults to config/keywords.yaml)
- `match_group(text, group_name)`: OR logic within group (any keyword match returns True)
- `match_job(job, source)`: AND logic between groups (tech required, location conditional)
- `_compile_patterns()`: Precompiles regex patterns for efficiency

**Smart Boundary Detection:**
1. CJK keywords (Chinese characters): Substring match using `re.escape()`
2. Short alphanumeric English keywords (<=3 chars like "AI", "NLP", "LLM"): Word boundary `\b` regex to prevent false positives
3. Longer keywords or keywords with special chars (like "C++", ".NET"): Substring match

**Critical Fix:**
- Initial implementation used word boundary for ALL short keywords (<=3 chars)
- This broke for "C++" because `\b` doesn't work with special characters
- Solution: Only use `\b` for alphanumeric-only keywords (`keyword.replace(' ', '').isalnum()`)

**Match Logic:**
- `match_group()`: Returns True if ANY keyword in the group matches (OR logic)
- `match_job()`: 
  - Always checks technology group (required)
  - Checks location group UNLESS source is in skip_location_for list
  - Combines job title, description, and tags into single text for matching
  - Handles tags as both list and string

### Test Coverage (32 tests, all passing)

**TestKeywordMatcher (2 tests):**
- Initialization with default path and config dict

**TestMatchGroup (13 tests):**
- English short keywords: exact match, no false positives ("AI" not in "email"/"wait"), case-insensitive
- English longer keywords: substring match
- Chinese keywords: substring match for CJK characters
- Mixed Chinese/English text
- OR logic within groups
- Empty text, invalid group names, no matches

**TestMatchJob (15 tests):**
- Jobs with tech+location, tech-only, location-only
- skip_location_for sources (remoteok, weworkremotely)
- Chinese content, mixed Chinese/English
- False positive prevention ("email", "waiting")
- Tags as list vs string
- Empty/missing fields
- Keywords in different fields (title, description, tags)

**TestEdgeCases (2 tests):**
- Special characters in keywords (C++, .NET, AI/ML)
- Multiple short keywords in same text
- Keywords at text boundaries
- Case variations

### Key Learnings

**Regex Word Boundaries:**
- `\b` only works between word characters (`\w`) and non-word characters
- `\b` does NOT work for keywords with special chars like "C++", ".NET", "AI/ML"
- Solution: Check if keyword is alphanumeric before applying word boundaries

**False Positive Prevention:**
- Short keywords like "AI" can match within longer words ("email", "wait", "train")
- Word boundary `\bAI\b` prevents these false positives
- But only for alphanumeric keywords — special chars need substring match

**CJK Text Handling:**
- Chinese text has no word boundaries
- Must use substring match for all CJK keywords
- Mixed Chinese/English text works correctly with both strategies

**Performance:**
- Precompiling regex patterns in `__init__` improves performance
- All patterns compiled once, reused for all matches
- `re.IGNORECASE` flag for case-insensitive matching

### Validation
- All 32 tests pass
- No false positives on "email", "waiting", "train"
- Chinese keywords match correctly
- Special character keywords (C++, .NET) work
- skip_location_for logic works for remoteok/weworkremotely
- Empty/missing fields handled gracefully

## Storage Manager Implementation - Task 4 Complete

### Files Created
- scraper/utils/storage.py (StorageManager class)
- tests/test_storage.py (16 comprehensive tests)

### Implementation Details

**StorageManager Features:**
- SQLite database with proper schema (15 columns including is_active)
- 4 indexes: source, company, is_active, first_seen
- upsert_job(): INSERT new or UPDATE existing, preserves first_seen, increments update_count
- get_all_jobs(): Returns deserialized JobPosting objects with active_only filter
- get_stats(): Returns total, active, inactive, by_source counts
- export_json(): Exports active jobs to JSON file with UTF-8 encoding

**Test Coverage (16 tests, all passing):**
- Database initialization (schema, tables, indexes)
- Insert new jobs
- Update existing jobs (preserves first_seen, increments update_count)
- Active/inactive filtering
- Correct deserialization of all fields including NULL values
- Statistics calculation
- JSON export (active only, creates parent dirs)
- Multiple upserts increment count correctly
- Special characters handling

**Windows Compatibility:**
- Fixed temp file cleanup with gc.collect() and retry logic for file locking

### Test Results
✅ 16/16 tests passed in 0.73s

### Key Design Decisions
- is_active is DB-only field (not in JobPosting model)
- Uses context managers for all DB connections
- Proper serialization via JobPosting.to_db_dict() and from_db_row()
- Tags stored as JSON string in SQLite
- Datetime fields stored as ISO format strings

## Task 6: EleduckAdapter Implementation (2026-02-10)

### API Structure
- Eleduck API returns JSON with 'posts' array (not a flat array like RemoteOK)
- Each post has: id, title, summary, user.nickname, tags (nested objects), published_at
- URL format: https://eleduck.com/posts/{id}
- Pagination: page parameter, returns 25 posts per page

### Implementation Details
- Added EleduckAdapter to existing scraper/adapters/api.py (same file as RemoteOKAdapter)
- Followed RemoteOKAdapter pattern closely for consistency
- Implemented pagination with configurable max_pages (default 5)
- Stops pagination when API returns empty posts array
- Uses _delay() between pages for rate limiting

### Field Mapping
- title: entry['title']
- company: entry['user']['nickname']
- description: entry['summary']
- tags: extracted from nested tag objects (tag['name'])
- published_at: ISO format datetime with timezone
- salary: None (not provided by API)
- location: None (embedded in tags, not separate field)

### Testing
- Created 18 tests following RemoteOK test pattern
- All tests use fixture data (no live API calls in tests)
- Fixed pagination test to mock multiple pages correctly
- Live smoke test: successfully fetched 25 jobs from API
- All 40 adapter tests pass (18 Eleduck + 22 RemoteOK)

## Task 7: WeWorkRemotely RSS Adapter (2026-02-10)

### RSS Feed Structure
- URL: `https://weworkremotely.com/remote-jobs.rss` (RSS 2.0)
- Returns 100 items per fetch
- Each `<item>` has: `<title>`, `<link>`, `<pubDate>`, `<description>`, `<category>`, `<region>`, `<type>`, `<skills>`, `<guid>`, `<expires_at>`
- Title format: `Company: Job Title` (split on first ": ")
- `<category>` maps to feedparser tags (list of dicts with 'term' key)
- `<region>` provides location (e.g., "Anywhere in the World", "Ontario")
- `<pubDate>` in RFC 2822 format, parsed with `email.utils.parsedate_to_datetime`
- Description is HTML-encoded in CDATA
- No structured salary field in RSS
- `<skills>` field exists but is comma-separated string, not used (tags from category are cleaner)

### Implementation Details
- Created `scraper/adapters/rss.py` with `WeWorkRemotelyAdapter(BaseAdapter)`
- Uses `feedparser.parse(xml_text)` — parse from string, not URL
- Company extracted from title via `_split_title()` static method
- Handles bozo_exception with warning log (continues processing)
- No pagination needed — single RSS fetch returns all entries

### Field Mapping
- `entry.title` → split into company + title
- `entry.link` → url
- `entry.published` → published_at (via parsedate_to_datetime)
- `entry.summary` → description
- `entry.tags[].term` → tags (from `<category>` element)
- `entry.region` → location (custom RSS extension)

### Testing
- 29 tests in 6 test classes, all passing
- TestWeWorkRemotelyAdapter: properties (2)
- TestTitleSplitting: company extraction edge cases (6)
- TestParseEntry: fixture-based field mapping (10)
- TestMissingFields: null/missing field handling (6)
- TestFetchJobs: mocked HTTP integration (3)
- TestIDGeneration: consistent ID hashing (2)
- Live smoke test: 100 jobs fetched successfully
- All 117 tests pass (29 WWR + 18 Eleduck + 22 RemoteOK + 48 others)

### Key Learnings
- feedparser auto-detects `<category>` elements as tags with `term` key
- feedparser exposes custom RSS elements like `<region>` as dict keys
- `email.utils.parsedate_to_datetime` handles RFC 2822 dates better than manual parsing
- xml.etree.ElementTree namespace handling mangles prefixes — use string slicing for fixture creation
- Windows print encoding issues with Unicode (e.g., ➡️) — use `io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`

## Task 8: CLI Entry Point & Orchestrator (2026-02-10)

### Files Created
- `scraper/orchestrator.py`: ScraperOrchestrator class
- `main.py`: CLI entry point with argparse subcommands

### ScraperOrchestrator Design
- `__init__()`: Loads sites.yaml, creates KeywordMatcher and StorageManager
- `run(site=None, dry_run=False)`: Main pipeline — fetch, match, store
- `_resolve_sites()`: Filters to enabled sites, optionally single site
- `_create_adapter()`: Maps site_id → adapter class via `_ADAPTER_MAP` dict
- `_scrape_site()`: Per-site fetch/match/store loop, mutates summary dict
- `interrupted` flag: Checked in loops for graceful Ctrl+C

### CLI Subcommands
- `scrape`: `--site`, `--dry-run`, parent `--verbose` flag
- `export`: `--format json`, `--output path`
- `stats`: No args, prints formatted database statistics

### Ctrl+C Handling
- SIGINT handler sets `orchestrator.interrupted = True`
- Both site loop and per-job matching loop check the flag
- Already-scraped data is saved before exiting
- Windows: SIGINT works fine (SIGTERM not reliable on Windows)

### Key Decisions
- JobPosting → dict conversion for matcher: extract title, description, tags
- Adapter mapping via dict lookup, not string-based dispatch
- Error handling per-site: catch Exception, log, continue to next site
- Summary dict mutated in place (simpler than returning + merging)

### Live Test Results
- All 3 sites scraped: 321 total, 94 matched, 94 new
- Stats: 40 remoteok, 27 eleduck, 27 weworkremotely
- Export: 94 jobs to data/exports/jobs.json
- Dry-run: 40 matched from remoteok, 0 saved
- All 117 existing tests still pass

## Task 9: Integration Tests & Final Verification (2026-02-10)

### Files Created
- `tests/test_integration.py`: 11 integration tests across 7 test classes

### Integration Test Scenarios (all passing)
1. **Full Pipeline** (TestFullPipeline): All 3 adapters mocked → fetch → match → store → verify DB has data
2. **Dry-Run** (TestDryRun): Fetch + match but verify nothing stored in DB
3. **Single-Site Filter** (TestSingleSiteFilter): Only RemoteOKAdapter invoked when site='remoteok'
4. **Error Handling** (TestErrorHandling): One adapter raises → others continue → error logged
5. **Stats After Scrape** (TestStatsAfterScrape): Counts match, upsert deduplication works
6. **Export After Scrape** (TestExportAfterScrape): Valid JSON, Chinese chars preserved, empty DB handled
7. **Component Integration** (TestComponentIntegration): Matcher filters correctly, model round-trip, all imports clean

### Mocking Strategy
- **Key insight**: Patching `httpx.Client` at module level with `MagicMock(spec=httpx.Client)` fails with "Cannot spec a Mock object" because the mock tries to spec another mock during context manager setup
- **Solution**: Patch `BaseAdapter._get_client` directly — this is the method adapters call, and we can dispatch based on `isinstance(self_adapter, RemoteOKAdapter)` etc.
- Plain `MagicMock()` (without spec) works fine for the client context manager

### Test Suite Summary
- **128 total tests** (117 existing + 11 new integration)
- All pass in ~2.9s on Windows

### Live Smoke Test Results
- `python main.py --verbose scrape`: 321 fetched, 94 matched, 94 updated (0 new — already in DB from Task 8)
- `python main.py stats`: 94 total (40 remoteok, 27 eleduck, 27 weworkremotely)
- `python main.py export --format json --output data/exports/jobs.json`: Valid JSON, 94 jobs
- Note: `--verbose` flag must come BEFORE the subcommand (argparse parent parser behavior)

### Final Quality Check
- All modules import cleanly
- No hardcoded secrets (API keys, tokens, passwords) in any .py or .yaml files
- No import errors
