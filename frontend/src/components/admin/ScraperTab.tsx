"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrapeRunsTable } from "@/components/dashboard/ScrapeRunsTable";
import {
  fetchSiteConfigs,
  fetchSchedulerStatus,
  fetchScrapeRuns,
  pauseScheduler,
  resumeScheduler,
  triggerScrape,
} from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { SiteConfig, SchedulerStatus, ScrapeRun } from "@/lib/types";
import {
  Play,
  Pause,
  Zap,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react";

export function ScraperTab() {
  const [sites, setSites] = useState<SiteConfig[]>([]);
  const [selectedSites, setSelectedSites] = useState<Set<string>>(new Set());
  const [dryRun, setDryRun] = useState(false);
  const [scraping, setScraping] = useState(false);

  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(true);
  const [schedulerUpdating, setSchedulerUpdating] = useState(false);

  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getToken = async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  };

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      const [siteData, schedulerData, runsData] = await Promise.all([
        fetchSiteConfigs(token),
        fetchSchedulerStatus(token).catch(() => null),
        fetchScrapeRuns(1, 10),
      ]);

      setSites(siteData);
      const enabledIds = new Set(
        siteData.filter((s) => s.enabled).map((s) => s.id),
      );
      setSelectedSites(enabledIds);

      if (schedulerData) setScheduler(schedulerData);
      setSchedulerLoading(false);

      setRuns(runsData.data);
      setRunsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const toggleSiteSelection = (siteId: string) => {
    setSelectedSites((prev) => {
      const next = new Set(prev);
      if (next.has(siteId)) next.delete(siteId);
      else next.add(siteId);
      return next;
    });
  };

  const handleTriggerScrape = async () => {
    if (selectedSites.size === 0) return;
    try {
      setScraping(true);
      setError(null);
      const token = await getToken();
      if (!token) return;
      await triggerScrape(token, {
        sites: Array.from(selectedSites),
        dry_run: dryRun,
      });
      const runsData = await fetchScrapeRuns(1, 10);
      setRuns(runsData.data);
    } catch {
      setError("Failed to trigger scrape");
    } finally {
      setScraping(false);
    }
  };

  const handlePauseResume = async () => {
    try {
      setSchedulerUpdating(true);
      const token = await getToken();
      if (!token) return;
      if (scheduler?.paused) {
        await resumeScheduler(token);
      } else {
        await pauseScheduler(token);
      }
      const status = await fetchSchedulerStatus(token);
      setScheduler(status);
    } catch {
      setError("Failed to update scheduler");
    } finally {
      setSchedulerUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="scraper-tab">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <Skeleton className="h-32 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="scraper-tab">
      {error && (
        <div
          className="flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-destructive text-sm"
          data-testid="scraper-error"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <Card data-testid="scrape-trigger-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Manual Scrape
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="mb-2 block text-sm font-medium">
              Select Sites
            </Label>
            <div
              className="flex flex-wrap gap-2"
              data-testid="site-select-group"
            >
              {sites.map((site) => (
                <button
                  key={site.id}
                  type="button"
                  onClick={() => toggleSiteSelection(site.id)}
                  data-testid="site-select-item"
                  className={`inline-flex items-center rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                    selectedSites.has(site.id)
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  {site.name}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Switch
              id="dry-run"
              checked={dryRun}
              onCheckedChange={setDryRun}
              data-testid="dry-run-toggle"
            />
            <Label htmlFor="dry-run">Dry Run (fetch &amp; match only, no save)</Label>
          </div>

          <Button
            onClick={handleTriggerScrape}
            disabled={scraping || selectedSites.size === 0}
            data-testid="start-scrape-btn"
          >
            {scraping ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            {scraping ? "Scraping…" : "Start Scrape"}
          </Button>
        </CardContent>
      </Card>

      <Card data-testid="scheduler-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Scheduler
          </CardTitle>
        </CardHeader>
        <CardContent>
          {schedulerLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : scheduler ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Status:</span>
                  <Badge
                    variant={
                      scheduler.paused
                        ? "outline"
                        : scheduler.running
                          ? "default"
                          : "secondary"
                    }
                    data-testid="scheduler-status"
                  >
                    {scheduler.paused
                      ? "Paused"
                      : scheduler.running
                        ? "Running"
                        : "Idle"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Interval:</span>
                  <span data-testid="scheduler-interval">
                    {scheduler.interval_minutes}m
                  </span>
                </div>
                {scheduler.next_run && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Next run:</span>
                    <span data-testid="scheduler-next-run">
                      {new Date(scheduler.next_run).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
              <Button
                variant={scheduler.paused ? "default" : "outline"}
                size="sm"
                onClick={handlePauseResume}
                disabled={schedulerUpdating}
                data-testid="scheduler-toggle-btn"
              >
                {schedulerUpdating ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : scheduler.paused ? (
                  <Play className="mr-2 h-4 w-4" />
                ) : (
                  <Pause className="mr-2 h-4 w-4" />
                )}
                {scheduler.paused ? "Resume" : "Pause"}
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Scheduler status unavailable.
            </p>
          )}
        </CardContent>
      </Card>

      <div data-testid="scraper-runs-section">
        {runsLoading ? (
          <Card>
            <CardContent className="pt-6">
              <Skeleton className="h-48 w-full" />
            </CardContent>
          </Card>
        ) : (
          <ScrapeRunsTable runs={runs} />
        )}
      </div>
    </div>
  );
}
