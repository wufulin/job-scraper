import Link from "next/link";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  ExternalLink,
  Heart,
  MapPin,
  Clock,
  DollarSign,
  Building2,
  Globe,
  CalendarDays,
  Tag,
} from "lucide-react";
import { fetchJob } from "@/lib/api";
import type { Job } from "@/lib/types";

const SOURCE_COLORS: Record<string, string> = {
  remoteok: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  eleduck: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  weworkremotely: "bg-sky-500/15 text-sky-700 dark:text-sky-400",
  v2ex: "bg-violet-500/15 text-violet-700 dark:text-violet-400",
  arcdev: "bg-rose-500/15 text-rose-700 dark:text-rose-400",
  workgo: "bg-teal-500/15 text-teal-700 dark:text-teal-400",
};

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    remoteok: "RemoteOK",
    eleduck: "Eleduck",
    weworkremotely: "WeWorkRemotely",
    v2ex: "V2EX",
    arcdev: "Arc.dev",
    workgo: "WorkGo",
  };
  return labels[source] ?? source;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "Unknown";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatRelativeDate(dateString: string | null): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

function isHtml(text: string): boolean {
  return /<[a-z][\s\S]*>/i.test(text);
}

function MetaItem({
  icon: Icon,
  label,
  value,
  testId,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  testId: string;
}) {
  return (
    <div className="flex items-start gap-3" data-testid={testId}>
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium truncate">{value}</p>
      </div>
    </div>
  );
}

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let job: Job;
  try {
    job = await fetchJob(id);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      notFound();
    }
    throw error;
  }

  const relativeDate = formatRelativeDate(job.published_at);

  return (
    <div data-testid="job-detail-page" className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/jobs">
          <Button
            variant="ghost"
            size="sm"
            data-testid="back-to-jobs"
            className="gap-2 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Back to Jobs
          </Button>
        </Link>
        <Button
          variant="outline"
          size="sm"
          data-testid="favorite-button"
          className="gap-2 text-muted-foreground hover:text-rose-500 hover:border-rose-500/30"
          aria-label="Add to favorites"
        >
          <Heart className="size-4" />
          <span className="hidden sm:inline">Favorite</span>
        </Button>
      </div>

      <Card data-testid="job-detail-header">
        <CardHeader className="space-y-4">
          <div className="flex items-center justify-between">
            <Badge
              variant="outline"
              className={`border-0 text-xs ${SOURCE_COLORS[job.source] ?? "bg-secondary text-secondary-foreground"}`}
              data-testid="job-detail-source"
            >
              {getSourceLabel(job.source)}
            </Badge>
            {relativeDate && (
              <span
                className="text-xs text-muted-foreground"
                data-testid="job-detail-relative-date"
              >
                {relativeDate}
              </span>
            )}
          </div>

          <h1
            className="text-2xl font-bold leading-tight tracking-tight sm:text-3xl"
            data-testid="job-detail-title"
          >
            {job.title}
          </h1>

          {job.tags.length > 0 && (
            <div
              className="flex flex-wrap gap-1.5"
              data-testid="job-detail-tags"
            >
              {job.tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-xs px-2 py-0.5"
                >
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </CardHeader>

        <Separator />

        <CardContent className="pt-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {job.company && (
              <MetaItem
                icon={Building2}
                label="Company"
                value={job.company}
                testId="job-detail-company"
              />
            )}
            {job.location && (
              <MetaItem
                icon={MapPin}
                label="Location"
                value={job.location}
                testId="job-detail-location"
              />
            )}
            {job.salary && (
              <MetaItem
                icon={DollarSign}
                label="Salary"
                value={job.salary}
                testId="job-detail-salary"
              />
            )}
            {job.published_at && (
              <MetaItem
                icon={CalendarDays}
                label="Published"
                value={formatDate(job.published_at)}
                testId="job-detail-published"
              />
            )}
            <MetaItem
              icon={Globe}
              label="Source"
              value={getSourceLabel(job.source)}
              testId="job-detail-source-meta"
            />
            {job.tags.length > 0 && (
              <MetaItem
                icon={Tag}
                label="Tags"
                value={job.tags.join(", ")}
                testId="job-detail-tags-meta"
              />
            )}
          </div>
        </CardContent>
      </Card>

      {job.description && (
        <Card data-testid="job-detail-description-card">
          <CardHeader>
            <h2 className="text-lg font-semibold">Job Description</h2>
          </CardHeader>
          <Separator />
          <CardContent className="pt-6">
            {isHtml(job.description) ? (
              <div
                className="job-description max-w-none text-sm leading-relaxed"
                data-testid="job-detail-description"
                dangerouslySetInnerHTML={{ __html: job.description }}
              />
            ) : (
              <div
                className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground"
                data-testid="job-detail-description"
              >
                {job.description}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="py-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Clock className="size-3" />
              First seen: {formatDate(job.first_seen)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock className="size-3" />
              Last seen: {formatDate(job.last_seen)}
            </span>
            {job.update_count > 0 && (
              <span data-testid="job-detail-update-count">
                Updated {job.update_count} time
                {job.update_count !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1"
          data-testid="view-original"
        >
          <Button className="w-full gap-2" size="lg">
            <ExternalLink className="size-4" />
            View Original Posting
          </Button>
        </a>
        <Link href="/jobs" className="flex-1 sm:flex-none">
          <Button
            variant="outline"
            className="w-full sm:w-auto gap-2"
            size="lg"
            data-testid="back-to-jobs-bottom"
          >
            <ArrowLeft className="size-4" />
            Back to Jobs
          </Button>
        </Link>
      </div>
    </div>
  );
}
