# Supabase Migrations

## Prerequisites

- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- A Supabase project (local or hosted)

## Directory Structure

```
supabase/
├── migrations/
│   ├── 001_initial_schema.sql   # 9 tables, indexes, triggers
│   └── 002_rls_policies.sql     # Row Level Security policies
├── seed.sql                     # Seed data from config/*.yaml
└── README.md
```

## Applying Migrations

### Option A: Supabase CLI (recommended)

```bash
# Link to your project
supabase link --project-ref <your-project-ref>

# Apply migrations
supabase db push

# Seed data
supabase db reset  # applies migrations + seed.sql
```

### Option B: Manual via SQL Editor

Run files in order in the Supabase Dashboard SQL Editor:

1. `migrations/001_initial_schema.sql`
2. `migrations/002_rls_policies.sql`
3. `seed.sql`

### Option C: psql

```bash
psql "$SUPABASE_DB_URL" -f supabase/migrations/001_initial_schema.sql
psql "$SUPABASE_DB_URL" -f supabase/migrations/002_rls_policies.sql
psql "$SUPABASE_DB_URL" -f supabase/seed.sql
```

## Tables

| Table | Purpose | RLS |
|-------|---------|-----|
| `jobs` | Scraped job postings | Read: auth + anon (active only) |
| `site_configs` | Source site configuration | Read: auth only |
| `keyword_configs` | Keywords per group | Read: auth only |
| `match_rules` | Matching rule definitions | Read: auth only |
| `profiles` | User profiles (auth.users) | Own data CRUD |
| `favorites` | User bookmarked jobs | Own data CRUD |
| `subscriptions` | Notification subscriptions | Own data CRUD |
| `notifications` | Sent notification log | Own data read |
| `scrape_runs` | Scrape execution audit log | Read: auth only |

## Key Design Decisions

- **`jobs.id` is `text`** (MD5 hex), not UUID — matches the existing Python `JobPosting.generate_id()` method
- **`timestamptz`** for all datetime fields (Supabase best practice)
- **`jsonb`** for `tags` and `extra_config` (flexible structured data)
- **`text[]`** arrays for multi-value fields like `skip_location_for`
- **`ON CONFLICT DO NOTHING`** in seed.sql for safe re-runs
- Backend writes use `service_role` key (bypasses RLS); never expose in client code
