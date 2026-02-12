"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import type { ScrapeRun } from "@/lib/types";

type TimelineChartProps = {
  runs: ScrapeRun[];
};

function buildTimelineData(runs: ScrapeRun[]) {
  const dailyMap = new Map<string, number>();

  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    dailyMap.set(key, 0);
  }

  for (const run of runs) {
    if (run.status !== "completed") continue;
    const day = run.started_at.slice(0, 10);
    if (dailyMap.has(day)) {
      dailyMap.set(day, (dailyMap.get(day) ?? 0) + (run.summary?.new ?? 0));
    }
  }

  return Array.from(dailyMap.entries()).map(([date, count]) => ({
    date,
    label: formatDateShort(date),
    jobs: count,
  }));
}

function formatDateShort(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function TimelineChart({ runs }: TimelineChartProps) {
  const chartData = buildTimelineData(runs);

  return (
    <Card data-testid="timeline-chart">
      <CardHeader>
        <CardTitle>New Jobs Over Time</CardTitle>
        <CardDescription>Jobs added per day (last 30 days)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 4, right: 4, left: -12, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                className="stroke-border"
                vertical={false}
              />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                className="fill-muted-foreground"
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 12 }}
                className="fill-muted-foreground"
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "var(--popover)",
                  color: "var(--popover-foreground)",
                  fontSize: "13px",
                }}
                labelFormatter={(_label, payload) => {
                  if (payload?.[0]?.payload?.date) {
                    return new Date(
                      payload[0].payload.date + "T00:00:00",
                    ).toLocaleDateString("en-US", {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    });
                  }
                  return _label;
                }}
              />
              <Line
                type="monotone"
                dataKey="jobs"
                stroke="oklch(0.488 0.243 264.376)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
