# Decisions

## 2026-02-10 Pre-Planning

### D1: Brainstorm doc (Feb 10) supersedes original design (Feb 7)
- Original had fatal flaws: wrong scraping strategies, broken keyword matching
- Brainstorm corrects architecture to adapter-based with verified API endpoints

### D2: Phase 1 MVP scope — synchronous, 3 sources only
- RemoteOK (API), 电鸭 (API), WeWorkRemotely (RSS)
- No async, no circuit breaker, no notifications, no cross-site dedup
- Simplest possible: fetch → match → store → print

### D3: Skip OfferShow entirely
- Site unreachable during research, likely behind Cloudflare
- Not worth the effort for uncertain returns

### D4: Python 3.11+ target
- Pydantic v2 works best with 3.10+
- Built-in generics (list[str]) require 3.9+
- 3.11+ for performance and modern features

### D5: Tests ship with code, not deferred
- Keyword matcher and each adapter get unit tests in the same task
- Critical-path testing, not full coverage
