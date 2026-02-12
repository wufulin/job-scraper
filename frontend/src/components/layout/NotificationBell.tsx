"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { getUnreadCount } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { NotificationSheet } from "@/components/notifications/NotificationSheet";

const POLL_INTERVAL_MS = 30_000;

export function NotificationBell() {
  const { user, accessToken } = useAuth();
  const [count, setCount] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshCount = useCallback(async () => {
    if (!accessToken) return;
    try {
      const res = await getUnreadCount(accessToken);
      setCount(res.count);
    } catch {
      /* empty */
    }
  }, [accessToken]);

  useEffect(() => {
    if (!user || !accessToken) {
      setCount(0);
      return;
    }

    refreshCount();
    intervalRef.current = setInterval(refreshCount, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [user, accessToken, refreshCount]);

  if (!user) return null;

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        data-testid="notification-bell"
        className="relative"
        onClick={() => setSheetOpen(true)}
      >
        <Bell className="h-4 w-4" />
        {count > 0 && (
          <span
            data-testid="notification-badge"
            className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground"
          >
            {count > 99 ? "99+" : count}
          </span>
        )}
        <span className="sr-only">Notifications</span>
      </Button>

      <NotificationSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onCountChange={refreshCount}
      />
    </>
  );
}
