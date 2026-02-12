import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowLeft, SearchX } from "lucide-react";

export default function JobNotFound() {
  return (
    <div
      data-testid="job-not-found"
      className="mx-auto flex max-w-lg flex-col items-center gap-6 py-16"
    >
      <div className="flex size-16 items-center justify-center rounded-2xl bg-muted">
        <SearchX className="size-8 text-muted-foreground" />
      </div>

      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-bold tracking-tight">Job not found</h1>
        <p className="text-sm text-muted-foreground max-w-md">
          The job posting you&apos;re looking for doesn&apos;t exist or may have
          been removed.
        </p>
      </div>

      <Link href="/jobs">
        <Button className="gap-2" data-testid="back-to-jobs">
          <ArrowLeft className="size-4" />
          Back to Jobs
        </Button>
      </Link>
    </div>
  );
}
