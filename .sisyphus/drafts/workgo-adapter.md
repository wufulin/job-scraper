# Draft: Add workgo.ai Adapter

## Requirements (confirmed)
- Add https://workgo.ai/ as a new data source for the job scraper
- Must follow existing adapter patterns (BaseAdapter ABC)

## Research Findings

### Site Architecture
- React SPA (Vite-built, fully client-side rendered)
- Server: nginx/1.24.0 (Ubuntu)
- Language: Chinese (zh-CN) with English support
- Focus: Global remote jobs for Chinese-speaking audience
- Auth: Clerk (clerk.workgo.ai) — mandatory for ALL job endpoints

### API Discovery
- Backend API at: https://api.workgo.ai
- Health endpoint: GET / → {"status": "healthy", "service": "workgo-api", "version": "1.0.0"}
- Main job endpoint: POST /auth/jobs/all (page, page_size params)
- Hot jobs: POST /auth/jobs/hot
- Job detail: GET /auth/jobs/{id}
- Search: /api/v1/search/* endpoints
- ALL /auth/* endpoints require Clerk JWT Bearer token
- No public/unauthenticated API for job listings
- No RSS feed available

### Pagination
- Parameters: page (default: 1), page_size (default: 20)
- Response includes: pagination.page, pagination.page_size, pagination.total, pagination.total_pages

### Job Fields (expected from API analysis)
- id, title, company, description, location, salary, job_type
- tags, skills_required, experience_level, published_at
- application_deadline, company_logo, benefits, remote_type

### Anti-Scraping
- robots.txt is permissive (only blocks /admin/, /login/)
- No explicit rate limiting documented
- Auth required = main barrier

### No Existing Scrapers
- Zero GitHub results for "workgo scraper"
- No public API documentation

## Critical Issue: Authentication Required
Unlike RemoteOK/Eleduck/WeWorkRemotely (public APIs), workgo.ai requires Clerk JWT auth.
This fundamentally changes the adapter approach.

## Open Questions
- Does user have a workgo.ai account?
- Approach: Playwright (browser automation) vs stored API token?
- Is the complexity worth it for this source?

## Scope Boundaries
- INCLUDE: TBD
- EXCLUDE: TBD
