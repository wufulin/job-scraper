"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BellOff, Check, CheckCheck, Loader2 } from "lucide-react";
import { supabase } from "@/lib/supabase";
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import type { Notification } from "@/lib/types";

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

interface NotificationSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCountChange?: () => void;
}

export function NotificationSheet({
  open,
  onOpenChange,
  onCountChange,
}: NotificationSheetProps) {
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      const res = await fetchNotifications(token, 1, 30);
      setNotifications(res.data);
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

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
        onCountChange?.();
      } catch {
        setNotifications((prev) =>
          prev.map((n) => (n.id === id ? { ...n, is_read: false } : n)),
        );
      }
    },
    [onCountChange],
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
      onCountChange?.();
    } catch {
      setNotifications(prev);
    } finally {
      setMarkingAll(false);
    }
  }, [notifications, onCountChange]);

  const handleClickNotification = useCallback(
    (n: Notification) => {
      if (!n.is_read) handleMarkRead(n.id);
      if (n.job_id) {
        onOpenChange(false);
        router.push(`/jobs/${n.job_id}`);
      }
    },
    [handleMarkRead, onOpenChange, router],
  );

  const hasUnread = notifications.some((n) => !n.is_read);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        data-testid="notification-sheet"
        className="flex flex-col p-0"
      >
        <SheetHeader className="border-b px-4 py-3">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-lg">Notifications</SheetTitle>
            {hasUnread && (
              <Button
                variant="ghost"
                size="sm"
                data-testid="mark-all-read"
                disabled={markingAll}
                onClick={handleMarkAllRead}
                className="text-xs h-7"
              >
                <CheckCheck className="size-3.5 mr-1" />
                Mark all read
              </Button>
            )}
          </div>
          <SheetDescription className="sr-only">
            Recent notifications
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto" data-testid="notification-list">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {!loading && notifications.length === 0 && (
            <div
              data-testid="notification-empty"
              className="flex flex-col items-center justify-center gap-2 py-16 text-center px-4"
            >
              <div className="rounded-full bg-muted p-3">
                <BellOff className="size-5 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">
                No notifications yet
              </p>
            </div>
          )}

          {!loading &&
            notifications.map((n) => (
              <button
                key={n.id}
                type="button"
                data-testid="notification-item"
                onClick={() => handleClickNotification(n)}
                className={`w-full text-left px-4 py-3 border-b border-border/40 transition-colors hover:bg-accent/50 flex gap-3 items-start ${
                  n.is_read ? "opacity-60" : ""
                }`}
              >
                <div
                  className={`mt-1.5 size-2 rounded-full shrink-0 ${
                    n.is_read ? "bg-transparent" : "bg-primary"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{n.title}</p>
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
                    className="size-7 shrink-0"
                    data-testid="mark-read"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleMarkRead(n.id);
                    }}
                  >
                    <Check className="size-3.5" />
                  </Button>
                )}
              </button>
            ))}
        </div>

        {!loading && notifications.length > 0 && (
          <div className="border-t p-3">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-xs"
              data-testid="view-all-notifications"
              onClick={() => {
                onOpenChange(false);
                router.push("/notifications");
              }}
            >
              View all notifications
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
