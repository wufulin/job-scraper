// ---------------------------------------------------------------------------
// TypeScript types matching backend API response models (app/models/responses.py)
// ---------------------------------------------------------------------------

/** Single job posting returned by the API. */
export interface Job {
  id: string;
  title: string;
  company: string | null;
  url: string;
  source: string;
  published_at: string | null;
  salary: string | null;
  location: string | null;
  description: string | null;
  tags: string[];
  first_seen: string;
  last_seen: string;
  last_updated: string;
  update_count: number;
}

/** Pagination metadata included in list responses. */
export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

/** Paginated list of jobs. */
export interface JobListResponse {
  data: Job[];
  pagination: PaginationMeta;
}

/** Job listing filters (client-side convenience). */
export interface JobFilters {
  search?: string;
  source?: string;
  page?: number;
  per_page?: number;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Admin — Site & Keyword config
// ---------------------------------------------------------------------------

export interface SiteConfig {
  id: string;
  name: string;
  url: string;
  adapter: string;
  enabled: boolean;
  skip_location_match: boolean;
  rate_limit_seconds: number;
  max_pages: number | null;
  config_json: string;
}

export interface SiteConfigUpdate {
  enabled?: boolean;
  rate_limit_seconds?: number;
  max_pages?: number | null;
  skip_location_match?: boolean;
  config_json?: string;
}

export interface KeywordConfig {
  id: number;
  group_name: string;
  keyword: string;
  enabled: boolean;
}

export interface KeywordCreate {
  group_name: string;
  keyword: string;
}

// ---------------------------------------------------------------------------
// Favorites
// ---------------------------------------------------------------------------

export interface Favorite {
  id: number;
  user_id: string;
  job_id: string;
  created_at: string;
}

export interface FavoriteListResponse {
  data: Favorite[];
  pagination: PaginationMeta;
}

// ---------------------------------------------------------------------------
// Stats & Scrape Runs
// ---------------------------------------------------------------------------

/** Stats summary returned by GET /api/stats. */
export interface StatsResponse {
  total: number;
  active: number;
  inactive: number;
  by_source: Record<string, number>;
}

/** Summary block inside a ScrapeRun. */
export interface ScrapeSummary {
  total_scraped: number;
  matched: number;
  dedup_removed: number;
  new: number;
  updated: number;
}

/** Single scrape run returned by GET /api/scrape/runs. */
export interface ScrapeRun {
  id: string;
  triggered_by: string | null;
  trigger_type: "manual" | "scheduled";
  sites: string[];
  status: "running" | "completed" | "failed" | "cancelled";
  dry_run: boolean;
  summary: ScrapeSummary;
  started_at: string;
  completed_at: string | null;
}

/** Paginated scrape runs response. */
export interface ScrapeRunListResponse {
  data: ScrapeRun[];
  pagination: PaginationMeta;
}

// ---------------------------------------------------------------------------
// Subscriptions
// ---------------------------------------------------------------------------

export interface Subscription {
  id: number;
  user_id: string;
  name: string;
  keywords: string[];
  match_mode: string;
  sources: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionListResponse {
  data: Subscription[];
  pagination: PaginationMeta;
}

export interface CreateSubscriptionRequest {
  name: string;
  keywords: string[];
  match_mode?: string;
  sources?: string[];
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string | null;
  job_id: string | null;
  is_read: boolean;
  email_sent: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  data: Notification[];
  pagination: PaginationMeta;
}

export interface UnreadCountResponse {
  count: number;
}

// ---------------------------------------------------------------------------
// Admin — Scheduler & Scrape Trigger
// ---------------------------------------------------------------------------

export interface SchedulerStatus {
  running: boolean;
  paused: boolean;
  next_run: string | null;
  interval_minutes: number;
}

export interface ScrapeRequest {
  sites: string[];
  dry_run: boolean;
}

export interface ScrapeResponse {
  run_id: string;
  status: string;
}
