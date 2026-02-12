import { Briefcase, TrendingUp, Globe, Clock } from "lucide-react";
import { fetchStats, fetchScrapeRuns } from "@/lib/api";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { SourceChart } from "@/components/dashboard/SourceChart";
import { TimelineChart } from "@/components/dashboard/TimelineChart";
import { ScrapeRunsTable } from "@/components/dashboard/ScrapeRunsTable";
import type { StatsResponse, ScrapeRun } from "@/lib/types";

function formatLastScrape(runs: ScrapeRun[]): string {
  const latest = runs.find((r) => r.status === "completed");
  if (!latest?.completed_at) return "Never";
  const d = new Date(latest.completed_at);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default async function DashboardPage() {
  let stats: StatsResponse | null = null;
  let runs: ScrapeRun[] = [];

  try {
    const [statsRes, runsRes] = await Promise.all([
      fetchStats(),
      fetchScrapeRuns(1, 20),
    ]);
    stats = statsRes;
    runs = runsRes.data;
  } catch {
    // API unavailable — render with empty state
  }

  const sourcesCount = stats ? Object.keys(stats.by_source).length : 0;
  const lastScrapeLabel = formatLastScrape(runs);

  return (
    <div data-testid="dashboard-page" className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of scraped job statistics.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          icon={<Briefcase className="h-4 w-4" />}
          title="Total Jobs"
          value={stats?.total ?? "—"}
        />
        <StatsCard
          icon={<TrendingUp className="h-4 w-4" />}
          title="Active"
          value={stats?.active ?? "—"}
        />
        <StatsCard
          icon={<Globe className="h-4 w-4" />}
          title="Sources"
          value={sourcesCount || "—"}
        />
        <StatsCard
          icon={<Clock className="h-4 w-4" />}
          title="Last Scrape"
          value={lastScrapeLabel}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SourceChart data={stats?.by_source ?? {}} />
        <TimelineChart runs={runs} />
      </div>

      <ScrapeRunsTable runs={runs} />
    </div>
  );
}
