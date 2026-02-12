"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, RefreshCw, AlertTriangle } from "lucide-react";

export default function JobDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      data-testid="job-detail-error"
      className="mx-auto flex max-w-lg flex-col items-center gap-6 py-16"
    >
      <div className="flex size-16 items-center justify-center rounded-2xl bg-destructive/10">
        <AlertTriangle className="size-8 text-destructive" />
      </div>

      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-bold tracking-tight">
          Something went wrong
        </h1>
        <p
          className="text-sm text-muted-foreground max-w-md"
          data-testid="job-detail-error-message"
        >
          {error.message || "Failed to load job details. Please try again."}
        </p>
      </div>

      <Card className="w-full">
        <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:justify-center">
          <Button
            onClick={reset}
            className="gap-2"
            data-testid="try-again-button"
          >
            <RefreshCw className="size-4" />
            Try Again
          </Button>
          <Link href="/jobs">
            <Button
              variant="outline"
              className="w-full gap-2"
              data-testid="back-to-jobs"
            >
              <ArrowLeft className="size-4" />
              Back to Jobs
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
