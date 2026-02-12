"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bell,
  BellOff,
  Plus,
  Pencil,
  Trash2,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import {
  fetchSubscriptions,
  deleteSubscription,
  toggleSubscription,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { SubscriptionDialog } from "@/components/subscriptions/SubscriptionDialog";
import type { Subscription } from "@/lib/types";

const SOURCE_LABELS: Record<string, string> = {
  remoteok: "RemoteOK",
  eleduck: "Eleduck",
  weworkremotely: "WWR",
  v2ex: "V2EX",
  arcdev: "Arc.dev",
};

export default function SubscriptionsPage() {
  const { user } = useAuth();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSub, setEditingSub] = useState<Subscription | null>(null);

  const loadSubscriptions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      const res = await fetchSubscriptions(token);
      setSubscriptions(res.data);
    } catch {
      setError("Failed to load subscriptions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) loadSubscriptions();
  }, [user, loadSubscriptions]);

  const handleToggle = useCallback(
    async (sub: Subscription) => {
      const prev = subscriptions;
      setSubscriptions((list) =>
        list.map((s) =>
          s.id === sub.id ? { ...s, is_active: !s.is_active } : s,
        ),
      );

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;
        await toggleSubscription(token, sub.id);
      } catch {
        setSubscriptions(prev);
      }
    },
    [subscriptions],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      const prev = subscriptions;
      setSubscriptions((list) => list.filter((s) => s.id !== id));

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;
        await deleteSubscription(token, id);
      } catch {
        setSubscriptions(prev);
      }
    },
    [subscriptions],
  );

  const handleEdit = useCallback((sub: Subscription) => {
    setEditingSub(sub);
    setDialogOpen(true);
  }, []);

  const handleCreate = useCallback(() => {
    setEditingSub(null);
    setDialogOpen(true);
  }, []);

  const handleDialogSaved = useCallback(() => {
    loadSubscriptions();
  }, [loadSubscriptions]);

  return (
    <div
      data-testid="subscriptions-page"
      className="flex flex-col gap-6 px-4 py-8 mx-auto max-w-3xl w-full"
    >
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold tracking-tight">Subscriptions</h1>
          <p className="text-muted-foreground">
            Get notified when new jobs match your criteria.
          </p>
        </div>
        <Button
          onClick={handleCreate}
          data-testid="create-subscription-button"
        >
          <Plus className="size-4 mr-1.5" />
          New
        </Button>
      </div>

      {loading && (
        <div data-testid="subscriptions-loading" className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      )}

      {!loading && error && (
        <div
          data-testid="subscriptions-error"
          className="flex flex-col items-center justify-center gap-3 py-16 text-center"
        >
          <div className="rounded-full bg-destructive/10 p-3">
            <Loader2 className="size-6 text-destructive" />
          </div>
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {!loading && !error && subscriptions.length === 0 && (
        <div
          data-testid="subscriptions-empty"
          className="flex flex-col items-center justify-center gap-3 py-16 text-center"
        >
          <div className="rounded-full bg-muted p-3">
            <BellOff className="size-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium">No subscriptions yet</p>
          <p className="text-xs text-muted-foreground max-w-sm">
            Create a subscription to get notified about jobs matching your
            keywords.
          </p>
        </div>
      )}

      {!loading && !error && subscriptions.length > 0 && (
        <div className="flex flex-col gap-3" data-testid="subscriptions-list">
          {subscriptions.map((sub) => (
            <Card
              key={sub.id}
              data-testid="subscription-card"
              className={`transition-opacity ${!sub.is_active ? "opacity-60" : ""}`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Bell
                      className={`size-4 shrink-0 ${
                        sub.is_active
                          ? "text-primary"
                          : "text-muted-foreground"
                      }`}
                    />
                    <CardTitle className="text-base truncate">
                      {sub.name}
                    </CardTitle>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Switch
                      data-testid="subscription-toggle"
                      checked={sub.is_active}
                      onCheckedChange={() => handleToggle(sub)}
                    />
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      data-testid="subscription-edit"
                      onClick={() => handleEdit(sub)}
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="text-muted-foreground hover:text-destructive"
                      data-testid="subscription-delete"
                      onClick={() => handleDelete(sub.id)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 pt-0">
                <div className="flex flex-wrap gap-1.5">
                  {sub.keywords.map((kw) => (
                    <Badge
                      key={kw}
                      variant="secondary"
                      className="text-[11px] px-1.5 py-0"
                    >
                      {kw}
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>
                    Match: <strong>{sub.match_mode}</strong>
                  </span>
                  {sub.sources.length > 0 && (
                    <span>
                      Sources:{" "}
                      {sub.sources
                        .map((s) => SOURCE_LABELS[s] ?? s)
                        .join(", ")}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <SubscriptionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        subscription={editingSub}
        onSaved={handleDialogSaved}
      />
    </div>
  );
}
