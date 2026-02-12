"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatsCardProps = {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  change?: { value: number; label: string };
};

export function StatsCard({ title, value, icon, change }: StatsCardProps) {
  return (
    <Card data-testid="stats-card">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <span className="text-muted-foreground">{icon}</span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tabular-nums">{value}</div>
        {change && (
          <p
            data-testid="stats-card-change"
            className={cn(
              "mt-1 text-xs",
              change.value > 0
                ? "text-emerald-600 dark:text-emerald-400"
                : change.value < 0
                  ? "text-red-500 dark:text-red-400"
                  : "text-muted-foreground",
            )}
          >
            {change.value > 0 ? "+" : ""}
            {change.value}% {change.label}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
