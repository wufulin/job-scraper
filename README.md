# Remote AI Job Scraper

Python CLI tool that scrapes remote AI/ML job postings from multiple sources, filters by configurable keywords, and stores results in SQLite.

## Features

- **7 data sources**: Scrapes from RemoteOK, Eleduck, WeWorkRemotely, V2EX, Arc.dev, WorkGo, and 远程.work
- **Async architecture**: Concurrent scraping with asyncio, httpx.AsyncClient, and aiosqlite for high throughput
- **Cross-site deduplication**: Fuzzy matching removes duplicate postings across different sources
- **Browser automation**: Playwright-based scraping for JavaScript-heavy sites (Arc.dev, WorkGo)
- **Smart keyword matching**: Supports CJK (Chinese, Japanese, Korean) characters for flexible job filtering
- **Async SQLite storage**: aiosqlite-based storage with upsert deduplication
- **JSON export**: Export matched jobs to JSON format for further analysis
- **Configurable keywords**: Customize job title and description matching via YAML config
- **Graceful interruption**: Ctrl+C handling saves partial results before exit
- **Rotating user agents**: Avoids detection by rotating request headers

## Data Sources

| Source | Type | Adapter | Status |
|--------|------|---------|--------|
| RemoteOK | JSON API | `api.py` | Enabled |
| Eleduck (电鸭) | JSON API | `api.py` | Enabled |
| WeWorkRemotely | RSS Feed | `rss.py` | Enabled |
| V2EX | Hybrid HTML+API | `hybrid.py` | Enabled |
| Arc.dev | Browser (Playwright) | `browser.py` | Enabled |
| WorkGo | Browser (Playwright) | `browser.py` | Disabled |
| 远程.work | HTML Scraping | `html.py` | Disabled |

## Quick Start

### Requirements

- Python 3.11 or higher
- (Optional) Playwright browsers for Arc.dev/WorkGo scraping: `playwright install chromium`

### Installation

```bash
git clone https://github.com/wufulin/job-scraper.git
cd job-scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### First Run

```bash
python main.py scrape
```

## Usage

### Scrape Jobs

Fetch jobs from all configured sources:

```bash
python main.py scrape
```

Enable verbose logging:

```bash
python main.py --verbose scrape
```

Note: The `--verbose` flag must come **before** the subcommand.

Scrape from a specific site:

```bash
python main.py scrape --site remoteok
python main.py scrape --site eleduck
python main.py scrape --site weworkremotely
python main.py scrape --site v2ex
python main.py scrape --site arcdev
python main.py scrape --site workgo
python main.py scrape --site yuancheng
```

Dry-run mode (fetch and match without saving):

```bash
python main.py scrape --dry-run
```

### View Statistics

Display database statistics:

```bash
python main.py stats
```

Shows total jobs, active/inactive counts, and breakdown by source.

### Export Jobs

Export all matched jobs to JSON:

```bash
python main.py export --format json
```

Export to a custom file:

```bash
python main.py export --format json --output path/to/file.json
```

## Configuration

### Sites Configuration

Edit `config/sites.yaml` to configure data sources. Each site has an adapter type, URL, and optional settings:

```yaml
remoteok:
  enabled: true
  adapter: api
  url: https://remoteok.com/api
  skip_location_match: true
  rate_limit_seconds: 2

eleduck:
  enabled: true
  adapter: api
  url: https://svc.eleduck.com/api/v1/posts
  params:
    category: 5
  max_pages: 5

weworkremotely:
  enabled: true
  adapter: rss
  url: https://weworkremotely.com/remote-jobs.rss
  skip_location_match: true

v2ex:
  enabled: true
  adapter: hybrid
  url: https://www.v2ex.com/go/remote
  api_base: https://www.v2ex.com/api/topics/show.json
  rate_limit_seconds: 6
  max_pages: 3

arcdev:
  enabled: true
  adapter: browser
  url: https://arc.dev/remote-jobs
  skip_location_match: true
```

### Keywords Configuration

Edit `config/keywords.yaml` to customize job matching. Jobs must match at least one keyword from each required group (AND between groups, OR within groups):

```yaml
keyword_groups:
  location:
    - "remote"
    - "远程"
    - "work from home"
  technology:
    - "AI"
    - "LLM"
    - "machine learning"
    - "GPT"
    - "大模型"

match_rules:
  default: "location AND technology"
  skip_location_for:
    - "remoteok"
    - "weworkremotely"
```

To add a new keyword, simply append it to the appropriate group in `config/keywords.yaml`. Short English keywords like "AI" and "NLP" use word-boundary matching to prevent false positives (e.g., "AI" won't match "email"). CJK keywords use substring matching.

### Environment Variables

The `.env.example` file lists environment variables: `PROXY_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `LOG_LEVEL` (planned for future features), and `WORKGO_EMAIL`/`WORKGO_PASSWORD` (WorkGo authentication credentials).

## Project Structure

```
job-scraper/
├── main.py                # CLI entry point (argparse + asyncio.run)
├── pyproject.toml         # Project metadata and dependencies
├── CLAUDE.md              # Claude Code project context
├── .gitignore
├── .env.example           # Environment variables (WorkGo auth, planned features)
├── config/
│   ├── sites.yaml         # Data source configuration (7 sites)
│   └── keywords.yaml      # Keyword matching rules
├── scraper/
│   ├── models.py          # Pydantic JobPosting model
│   ├── logger.py          # Loguru logging setup
│   ├── orchestrator.py    # Async scraping pipeline with dedup
│   ├── adapters/
│   │   ├── base.py        # BaseAdapter ABC (async)
│   │   ├── api.py         # RemoteOKAdapter, EleduckAdapter
│   │   ├── rss.py         # WeWorkRemotelyAdapter
│   │   ├── browser.py     # WorkGoAdapter, ArcDevAdapter (Playwright)
│   │   ├── hybrid.py      # V2EXAdapter (HTML + API)
│   │   └── html.py        # YuanchengAdapter (BeautifulSoup)
│   └── utils/
│       ├── matcher.py     # Keyword matching with CJK support
│       ├── storage.py     # Async SQLite storage (aiosqlite)
│       └── dedup.py       # Cross-site deduplication
├── tests/                 # 314 tests
│   ├── test_matcher.py
│   ├── test_storage.py
│   ├── test_integration.py
│   ├── test_dedup.py
│   ├── test_adapters/
│   │   ├── test_remoteok.py
│   │   ├── test_eleduck.py
│   │   ├── test_wwr.py
│   │   ├── test_workgo.py
│   │   ├── test_v2ex.py
│   │   ├── test_arcdev.py
│   │   └── test_yuancheng.py
│   └── fixtures/          # Sample API/RSS/HTML responses
├── docs/                  # Design documents (Chinese)
├── data/                  # SQLite DB and exports (gitignored)
└── logs/                  # Log files (gitignored)
```

## Architecture

```
CLI (main.py + asyncio.run)
    ↓
Orchestrator (async, asyncio.gather with semaphore)
    ↓
Adapters (7 sources: API, RSS, Browser, Hybrid, HTML)
    ↓
Matcher (keyword filtering)
    ↓
Cross-site Dedup (DedupManager)
    ↓
Storage (async SQLite via aiosqlite)
```

The orchestrator coordinates the scraping pipeline:
1. Initializes adapters for enabled sources
2. Fetches jobs concurrently (asyncio.gather with semaphore of 3)
3. Applies keyword matching to filter results
4. Runs cross-site deduplication (fuzzy company+title matching)
5. Stores deduplicated results in async SQLite
6. Returns summary statistics

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

The project includes 314 tests covering all 7 adapters, matching logic, storage operations, deduplication, integration tests, and CLI commands. Tests complete in approximately 9 seconds.

## Tech Stack

- **httpx**: Async HTTP client (httpx.AsyncClient) for API requests
- **aiosqlite**: Async SQLite database access
- **playwright**: Browser automation for JavaScript-heavy sites
- **feedparser**: RSS feed parsing for WeWorkRemotely
- **beautifulsoup4**: HTML parsing for V2EX and Yuancheng adapters
- **Pydantic v2**: Data validation and serialization
- **loguru**: Structured logging
- **fake-useragent**: Rotating user agents for requests
- **chardet**: Character encoding detection
- **pyyaml**: YAML configuration parsing
- **pytest-asyncio**: Async test support

## Roadmap

### Phase 1 (Complete)
- ✓ RemoteOK, Eleduck, WeWorkRemotely sources
- ✓ Keyword matching with CJK support
- ✓ SQLite storage with deduplication
- ✓ JSON export
- ✓ CLI with scrape/stats/export commands

### Phase 2 (Complete)
- ✓ Async migration (httpx.AsyncClient + aiosqlite)
- ✓ V2EX job board integration (hybrid HTML+API)
- ✓ Arc.dev integration (Playwright browser automation)
- ✓ WorkGo integration (Playwright with Clerk auth)
- ✓ 远程.work integration (HTML scraping, disabled — domain redirects)
- ✓ Cross-site deduplication
- ✓ Concurrent scraping with asyncio.gather

### Phase 3
- Email/Slack notifications for new matches
- Docker containerization

### Phase 4
- Job scoring and ranking
- Notion database integration

## License

MIT License - see LICENSE file for details
