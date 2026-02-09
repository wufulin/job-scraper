# Remote AI Job Scraper

Python CLI tool that scrapes remote AI/ML job postings from multiple sources, filters by configurable keywords, and stores results in SQLite.

## Features

- **Multiple data sources**: Scrapes from RemoteOK, Eleduck (电鸭), and WeWorkRemotely
- **Smart keyword matching**: Supports CJK (Chinese, Japanese, Korean) characters for flexible job filtering
- **SQLite with upsert deduplication**: Efficient storage with automatic duplicate detection
- **JSON export**: Export matched jobs to JSON format for further analysis
- **Configurable keywords**: Customize job title and description matching via YAML config
- **Graceful interruption**: Ctrl+C handling saves partial results before exit
- **Rotating user agents**: Avoids detection by rotating request headers

## Data Sources

| Source | Type | Coverage |
|--------|------|----------|
| RemoteOK | JSON API | Global remote jobs |
| Eleduck (电鸭) | JSON API | Chinese remote jobs |
| WeWorkRemotely | RSS Feed | English remote jobs |

## Quick Start

### Requirements

- Python 3.11 or higher

### Installation

```bash
git clone https://github.com/yourusername/job-scraper.git
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

## Project Structure

```
job-scraper/
├── main.py                # CLI entry point (argparse)
├── pyproject.toml         # Project metadata and dependencies
├── .gitignore
├── .env.example           # Environment variable template
├── config/
│   ├── sites.yaml         # Data source configuration
│   └── keywords.yaml      # Keyword matching rules
├── scraper/
│   ├── models.py          # Pydantic JobPosting model
│   ├── logger.py          # Loguru logging setup
│   ├── orchestrator.py    # Main scraping pipeline
│   ├── adapters/
│   │   ├── base.py        # BaseAdapter ABC
│   │   ├── api.py         # RemoteOKAdapter, EleduckAdapter
│   │   └── rss.py         # WeWorkRemotelyAdapter
│   └── utils/
│       ├── matcher.py     # Keyword matching with CJK support
│       └── storage.py     # SQLite storage with upsert
├── tests/                 # 128 tests
│   ├── test_matcher.py
│   ├── test_storage.py
│   ├── test_integration.py
│   ├── test_adapters/
│   │   ├── test_remoteok.py
│   │   ├── test_eleduck.py
│   │   └── test_wwr.py
│   └── fixtures/          # Sample API/RSS responses
├── data/                  # SQLite DB and exports (gitignored)
└── logs/                  # Log files (gitignored)
```

## Architecture

```
CLI (main.py)
    ↓
Orchestrator (orchestrator.py)
    ↓
Adapters (remoteok, eleduck, weworkremotely)
    ↓
Matcher (keyword filtering)
    ↓
Storage (SQLite with upsert)
```

The orchestrator coordinates the scraping pipeline:
1. Initializes adapters for enabled sources
2. Fetches jobs from each source
3. Applies keyword matching to filter results
4. Deduplicates and stores in SQLite
5. Returns summary statistics

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

The project includes 128 tests covering adapters, matching logic, storage operations, and CLI commands. Tests complete in approximately 2.9 seconds.

## Tech Stack

- **httpx**: Synchronous HTTP client for API requests
- **feedparser**: RSS feed parsing for WeWorkRemotely
- **Pydantic v2**: Data validation and serialization
- **SQLite**: Lightweight database for job storage
- **loguru**: Structured logging
- **fake-useragent**: Rotating user agents for requests
- **chardet**: Character encoding detection
- **beautifulsoup4**: HTML parsing (optional, for future enhancements)
- **pyyaml**: YAML configuration parsing

## Roadmap

### Phase 1 (Current)
- ✓ RemoteOK, Eleduck, WeWorkRemotely sources
- ✓ Keyword matching with CJK support
- ✓ SQLite storage with deduplication
- ✓ JSON export
- ✓ CLI with scrape/stats/export commands

### Phase 2
- V2EX job board integration
- Arc.dev integration
- Asynchronous scraping for improved performance

### Phase 3
- Email/Slack notifications for new matches
- Docker containerization

### Phase 4
- Job scoring and ranking
- Notion database integration

## License

MIT License - see LICENSE file for details
