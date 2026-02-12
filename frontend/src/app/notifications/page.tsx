"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Notification, PaginationMeta } from "@/lib/types";

type FilterMode = "all" | "unread" | "read";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function typeLabel(type: string): string {
  switch (type) {
    case "new_match":
      return "New Match";
    case "scrape_complete":
      return "Scrape Done";
    case "system":
      return "System";
    default:
      return type;
  }
}

export default function NotificationsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;
        const res = await fetchNotifications(token, p, 20);
        setNotifications(res.data);
        setPagination(res.pagination);
      } catch {
        setError("Failed to load notifications");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (user) load(page);
  }, [user, page, load]);

  const handleMarkRead = useCallback(
    async (id: string) => {
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;
        await markNotificationRead(token, id);
      } catch {
        setNotifications((prev) =>
          prev.map((n) => (n.id === id ? { ...n, is_read: false } : n)),
        );
      }
    },
    [],
  );

  const handleMarkAllRead = useCallback(async () => {
    setMarkingAll(true);
    const prev = notifications;
    setNotifications((list) => list.map((n) => ({ ...n, is_read: true })));
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      await markAllNotificationsRead(token);
    } catch {
      setNotifications(prev);
    } finally {
      setMarkingAll(false);
    }
  }, [notifications]);

  const handleClick = useCallback(
    (n: Notification) => {
      if (!n.is_read) handleMarkRead(n.id);
      if (n.job_id) router.push(`/jobs/${n.job_id}`);
    },
    [handleMarkRead, router],
  );

  const filtered = notifications.filter((n) => {
    if (filter === "unread") return !n.is_read;
    if (filter === "read") return n.is_read;
    return true;
  });

  const hasUnread = notifications.some((n) => !n.is_read);

  return (
    <div
      data-testid="notifications-page"
      className="flex flex-col gap-6 px-4 py-8 mx-auto max-w-3xl w-full"
    >
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Bell className="size-7" />
            Notifications
          </h1>
          <p className="text-muted-foreground">
            Stay updated on new job matches and system events.
          </p>
        </div>
        {hasUnread && (
          <Button
            variant="outline"
            size="sm"
            data-testid="mark-all-read-page"
            disabled={markingAll}
            onClick={handleMarkAllRead}
          >
            <CheckCheck className="size-4 mr-1.5" />
            Mark all read
          </Button>
        )}
      </div>

      <div className="flex gap-2" data-testid="notification-filters">
        {(["all", "unread", "read"] as FilterMode[]).map((mode) => (
          <Button
            key={mode}
            variant={filter === mode ? "default" : "outline"}
            size="sm"
            className="capitalize text-xs h-7"
            onClick={() => {
              setFilter(mode);
              setPage(1);
            }}
          >
            {mode}
          </Button>
        ))}
      </div>

      {loading && (
        <div
          data-testid="notifications-loading"
          className="flex items-center justify-center py-16"
        >
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && error && (
        <div
          data-testid="notifications-error"
          className="flex flex-col items-center justify-center gap-3 py-16 text-center"
        >
          <div className="rounded-full bg-destructive/10 p-3">
            <Loader2 className="size-6 text-destructive" />
          </div>
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div
          data-testid="notifications-empty"
          className="flex flex-col items-center justify-center gap-2 py-16 text-center"
        >
          <div className="rounded-full bg-muted p-3">
            <BellOff className="size-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium text-muted-foreground">
            {filter === "all"
              ? "No notifications yet"
              : `No ${filter} notifications`}
          </p>
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div
          className="rounded-lg border divide-y"
          data-testid="notifications-list"
        >
          {filtered.map((n) => (
            <button
              key={n.id}
              type="button"
              data-testid="notification-row"
              onClick={() => handleClick(n)}
              className={`w-full text-left px-4 py-3.5 flex gap-3 items-start transition-colors hover:bg-accent/50 ${
                n.is_read ? "opacity-60" : ""
              } ${n.job_id ? "cursor-pointer" : "cursor-default"}`}
            >
              <div
                className={`mt-1.5 size-2.5 rounded-full shrink-0 ${
                  n.is_read ? "bg-muted" : "bg-primary"
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium truncate">{n.title}</p>
                  <Badge
                    variant="secondary"
                    className="text-[10px] px-1.5 py-0 shrink-0"
                  >
                    {typeLabel(n.type)}
                  </Badge>
                </div>
                {n.body && (
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                    {n.body}
                  </p>
                )}
                <p className="text-[11px] text-muted-foreground/70 mt-1">
                  {timeAgo(n.created_at)}
                </p>
              </div>
              {!n.is_read && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 shrink-0"
                  data-testid="notification-mark-read"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleMarkRead(n.id);
                  }}
                >
                  <Check className="size-4" />
                </Button>
              )}
            </button>
          ))}
        </div>
      )}

      {pagination && pagination.total_pages > 1 && (
        <div
          className="flex items-center justify-center gap-2"
          data-testid="notifications-pagination"
        >
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="text-sm text-muted-foreground tabular-nums">
            {page} / {pagination.total_pages}
          </span>
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            disabled={page >= pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
