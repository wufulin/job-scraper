"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

const SOURCE_COLORS: Record<string, string> = {
  remoteok: "oklch(0.646 0.222 41.116)",
  eleduck: "oklch(0.6 0.118 184.704)",
  weworkremotely: "oklch(0.398 0.07 227.392)",
  v2ex: "oklch(0.828 0.189 84.429)",
  arcdev: "oklch(0.769 0.188 70.08)",
  workgo: "oklch(0.488 0.243 264.376)",
  yuancheng: "oklch(0.696 0.17 162.48)",
};

const FALLBACK_COLOR = "oklch(0.552 0.016 285.938)";

type SourceChartProps = {
  data: Record<string, number>;
};

export function SourceChart({ data }: SourceChartProps) {
  const chartData = Object.entries(data)
    .map(([source, count]) => ({ source, count }))
    .sort((a, b) => b.count - a.count);

  if (chartData.length === 0) {
    return (
      <Card data-testid="source-chart">
        <CardHeader>
          <CardTitle>Jobs by Source</CardTitle>
          <CardDescription>No source data available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card data-testid="source-chart">
      <CardHeader>
        <CardTitle>Jobs by Source</CardTitle>
        <CardDescription>Distribution across scrape targets</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 4, right: 4, left: -12, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                className="stroke-border"
                vertical={false}
              />
              <XAxis
                dataKey="source"
                tick={{ fontSize: 12 }}
                className="fill-muted-foreground"
                tickLine={false}
                axisLine={false}
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
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={48}>
                {chartData.map((entry) => (
                  <Cell
                    key={entry.source}
                    fill={SOURCE_COLORS[entry.source] ?? FALLBACK_COLOR}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
