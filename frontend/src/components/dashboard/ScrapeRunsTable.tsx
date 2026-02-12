"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ScrapeRun } from "@/lib/types";

type ScrapeRunsTableProps = {
  runs: ScrapeRun[];
};

const STATUS_VARIANT: Record<
  ScrapeRun["status"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  running: "default",
  completed: "secondary",
  failed: "destructive",
  cancelled: "outline",
};

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ScrapeRunsTable({ runs }: ScrapeRunsTableProps) {
  if (runs.length === 0) {
    return (
      <Card data-testid="scrape-runs-table">
        <CardHeader>
          <CardTitle>Recent Scrape Runs</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No scrape runs yet.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="scrape-runs-table">
      <CardHeader>
        <CardTitle>Recent Scrape Runs</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Trigger</TableHead>
              <TableHead>Sites</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Summary</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id} data-testid="scrape-run-row">
                <TableCell className="font-medium">
                  {formatDateTime(run.started_at)}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" data-testid="trigger-badge">
                    {run.trigger_type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {run.sites.map((site) => (
                      <Badge
                        key={site}
                        variant="secondary"
                        className="text-[11px]"
                        data-testid="site-badge"
                      >
                        {site}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={STATUS_VARIANT[run.status]}
                    data-testid="status-badge"
                  >
                    {run.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {run.summary ? (
                    <span
                      className="text-sm text-muted-foreground"
                      data-testid="run-summary"
                    >
                      {run.summary.total_scraped} scraped / {run.summary.matched}{" "}
                      matched / {run.summary.new} new
                    </span>
                  ) : (
                    <span className="text-sm text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
