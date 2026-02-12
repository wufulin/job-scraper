import type {
  JobListResponse,
  Job,
  JobFilters,
  TokenResponse,
  User,
  StatsResponse,
  ScrapeRunListResponse,
  FavoriteListResponse,
  Subscription,
  SubscriptionListResponse,
  CreateSubscriptionRequest,
  NotificationListResponse,
  UnreadCountResponse,
  SiteConfig,
  SiteConfigUpdate,
  KeywordConfig,
  KeywordCreate,
  SchedulerStatus,
  ScrapeRequest,
  ScrapeResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  params?: Record<string, string>;
  signal?: AbortSignal;
};

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
    }
    return url.toString();
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, headers = {}, params, signal } = options;

    const url = this.buildUrl(path, params);

    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });

    if (!response.ok) {
      const errorBody = await response.text().catch(() => "Unknown error");
      throw new Error(
        `API Error ${response.status}: ${response.statusText} - ${errorBody}`,
      );
    }

    return response.json() as Promise<T>;
  }

  get<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  post<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, "method" | "body">,
  ) {
    return this.request<T>(path, { ...options, method: "POST", body });
  }

  put<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, "method" | "body">,
  ) {
    return this.request<T>(path, { ...options, method: "PUT", body });
  }

  patch<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, "method" | "body">,
  ) {
    return this.request<T>(path, { ...options, method: "PATCH", body });
  }

  delete<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }
}

export const api = new ApiClient(API_BASE_URL);

export function fetchJobs(filters?: JobFilters): Promise<JobListResponse> {
  const params: Record<string, string> = {};
  if (filters?.page) params.page = String(filters.page);
  if (filters?.per_page) params.per_page = String(filters.per_page);
  if (filters?.source) params.source = filters.source;
  if (filters?.search) params.search = filters.search;
  return api.get<JobListResponse>("/jobs", { params });
}

export function fetchJob(id: string): Promise<Job> {
  return api.get<Job>(`/jobs/${id}`);
}

export function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return api.post<TokenResponse>("/auth/login", { email, password });
}

export function register(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return api.post<TokenResponse>("/auth/register", { email, password });
}

export function fetchCurrentUser(token: string): Promise<User> {
  return api.get<User>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchStats(): Promise<StatsResponse> {
  return api.get<StatsResponse>("/stats");
}

export function fetchScrapeRuns(
  page = 1,
  perPage = 10,
): Promise<ScrapeRunListResponse> {
  return api.get<ScrapeRunListResponse>("/scrape/runs", {
    params: { page: String(page), per_page: String(perPage) },
  });
}

// ---------------------------------------------------------------------------
// Favorites
// ---------------------------------------------------------------------------

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export function fetchFavorites(
  token: string,
  page = 1,
  perPage = 50,
): Promise<FavoriteListResponse> {
  return api.get<FavoriteListResponse>("/favorites", {
    headers: authHeaders(token),
    params: { page: String(page), per_page: String(perPage) },
  });
}

export function addFavorite(
  token: string,
  jobId: string,
): Promise<{ id: number }> {
  return api.post<{ id: number }>("/favorites", { job_id: jobId }, {
    headers: authHeaders(token),
  });
}

export function removeFavorite(
  token: string,
  jobId: string,
): Promise<void> {
  return api.delete<void>(`/favorites/${jobId}`, {
    headers: authHeaders(token),
  });
}

// ---------------------------------------------------------------------------
// Subscriptions
// ---------------------------------------------------------------------------

export function fetchSubscriptions(
  token: string,
  page = 1,
  perPage = 50,
): Promise<SubscriptionListResponse> {
  return api.get<SubscriptionListResponse>("/subscriptions", {
    headers: authHeaders(token),
    params: { page: String(page), per_page: String(perPage) },
  });
}

export function createSubscription(
  token: string,
  data: CreateSubscriptionRequest,
): Promise<Subscription> {
  return api.post<Subscription>("/subscriptions", data, {
    headers: authHeaders(token),
  });
}

export function updateSubscription(
  token: string,
  id: number,
  data: Partial<CreateSubscriptionRequest>,
): Promise<Subscription> {
  return api.put<Subscription>(`/subscriptions/${id}`, data, {
    headers: authHeaders(token),
  });
}

export function deleteSubscription(
  token: string,
  id: number,
): Promise<void> {
  return api.delete<void>(`/subscriptions/${id}`, {
    headers: authHeaders(token),
  });
}

export function toggleSubscription(
  token: string,
  id: number,
): Promise<Subscription> {
  return api.post<Subscription>(`/subscriptions/${id}/toggle`, undefined, {
    headers: authHeaders(token),
  });
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export function fetchNotifications(
  token: string,
  page = 1,
  perPage = 20,
): Promise<NotificationListResponse> {
  return api.get<NotificationListResponse>("/notifications", {
    headers: authHeaders(token),
    params: { page: String(page), per_page: String(perPage) },
  });
}

export function getUnreadCount(
  token: string,
): Promise<UnreadCountResponse> {
  return api.get<UnreadCountResponse>("/notifications/unread-count", {
    headers: authHeaders(token),
  });
}

export function markNotificationRead(
  token: string,
  id: string,
): Promise<void> {
  return api.post<void>(`/notifications/${id}/read`, undefined, {
    headers: authHeaders(token),
  });
}

export function markAllNotificationsRead(
  token: string,
): Promise<void> {
  return api.post<void>("/notifications/read-all", undefined, {
    headers: authHeaders(token),
  });
}

export function fetchSiteConfigs(token: string): Promise<SiteConfig[]> {
  return api.get<SiteConfig[]>("/config/sites", {
    headers: authHeaders(token),
  });
}

export function updateSiteConfig(
  token: string,
  siteId: string,
  data: SiteConfigUpdate,
): Promise<SiteConfig> {
  return api.put<SiteConfig>(`/config/sites/${siteId}`, data, {
    headers: authHeaders(token),
  });
}

export function fetchKeywordConfigs(token: string): Promise<KeywordConfig[]> {
  return api.get<KeywordConfig[]>("/config/keywords", {
    headers: authHeaders(token),
  });
}

export function createKeyword(
  token: string,
  data: KeywordCreate,
): Promise<KeywordConfig> {
  return api.post<KeywordConfig>("/config/keywords", data, {
    headers: authHeaders(token),
  });
}

export function updateKeyword(
  token: string,
  id: number,
  data: Partial<KeywordConfig>,
): Promise<KeywordConfig> {
  return api.put<KeywordConfig>(`/config/keywords/${id}`, data, {
    headers: authHeaders(token),
  });
}

export function deleteKeyword(
  token: string,
  id: number,
): Promise<void> {
  return api.delete<void>(`/config/keywords/${id}`, {
    headers: authHeaders(token),
  });
}

export function fetchSchedulerStatus(token: string): Promise<SchedulerStatus> {
  return api.get<SchedulerStatus>("/scheduler/status", {
    headers: authHeaders(token),
  });
}

export function pauseScheduler(token: string): Promise<void> {
  return api.post<void>("/scheduler/pause", undefined, {
    headers: authHeaders(token),
  });
}

export function resumeScheduler(token: string): Promise<void> {
  return api.post<void>("/scheduler/resume", undefined, {
    headers: authHeaders(token),
  });
}

export function triggerScrape(
  token: string,
  data: ScrapeRequest,
): Promise<ScrapeResponse> {
  return api.post<ScrapeResponse>("/scrape", data, {
    headers: authHeaders(token),
  });
}
