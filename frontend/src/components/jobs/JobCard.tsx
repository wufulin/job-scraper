"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { Heart, ExternalLink, MapPin, Clock, DollarSign } from "lucide-react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { addFavorite, removeFavorite } from "@/lib/api";
import type { Job } from "@/lib/types";

const SOURCE_COLORS: Record<string, string> = {
  remoteok: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  eleduck: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  weworkremotely: "bg-sky-500/15 text-sky-700 dark:text-sky-400",
  v2ex: "bg-violet-500/15 text-violet-700 dark:text-violet-400",
  arcdev: "bg-rose-500/15 text-rose-700 dark:text-rose-400",
  workgo: "bg-teal-500/15 text-teal-700 dark:text-teal-400",
};

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

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    remoteok: "RemoteOK",
    eleduck: "Eleduck",
    weworkremotely: "WWR",
    v2ex: "V2EX",
    arcdev: "Arc.dev",
    workgo: "WorkGo",
  };
  return labels[source] ?? source;
}

interface JobCardProps {
  job: Job;
  isFavorited?: boolean;
  onFavoriteChange?: (jobId: string, favorited: boolean) => void;
}

export function JobCard({ job, isFavorited = false, onFavoriteChange }: JobCardProps) {
  const { user } = useAuth();
  const [favorited, setFavorited] = useState(isFavorited);
  const [toggling, setToggling] = useState(false);

  const handleToggleFavorite = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!user || toggling) return;

      const prev = favorited;
      setFavorited(!prev);
      setToggling(true);

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;

        if (prev) {
          await removeFavorite(token, job.id);
        } else {
          await addFavorite(token, job.id);
        }
        onFavoriteChange?.(job.id, !prev);
      } catch {
        setFavorited(prev);
      } finally {
        setToggling(false);
      }
    },
    [user, toggling, favorited, job.id, onFavoriteChange],
  );

  return (
    <Card
      data-testid="job-card"
      className="group relative transition-all duration-200 hover:shadow-md hover:border-primary/20"
    >
      <CardHeader className="pb-0 gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <Link
              href={`/jobs/${job.id}`}
              className="block"
              data-testid="job-card-link"
            >
              <CardTitle className="text-base leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                {job.title}
              </CardTitle>
            </Link>
            {job.company && (
              <p
                className="text-sm text-muted-foreground font-medium truncate"
                data-testid="job-card-company"
              >
                {job.company}
              </p>
            )}
          </div>
          {user && (
            <Button
              variant="ghost"
              size="icon-xs"
              className={`shrink-0 transition-colors ${
                favorited
                  ? "text-rose-500 hover:text-rose-600"
                  : "text-muted-foreground hover:text-rose-500"
              }`}
              data-testid="job-card-favorite"
              aria-label={favorited ? "Remove from favorites" : "Add to favorites"}
              disabled={toggling}
              onClick={handleToggleFavorite}
            >
              <Heart className={`size-4 ${favorited ? "fill-current" : ""}`} />
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground">
          {job.location && (
            <span className="inline-flex items-center gap-1" data-testid="job-card-location">
              <MapPin className="size-3" />
              <span className="truncate max-w-[140px]">{job.location}</span>
            </span>
          )}
          {job.salary && (
            <span className="inline-flex items-center gap-1" data-testid="job-card-salary">
              <DollarSign className="size-3" />
              <span className="truncate max-w-[180px]">{job.salary}</span>
            </span>
          )}
          {job.published_at && (
            <span className="inline-flex items-center gap-1" data-testid="job-card-date">
              <Clock className="size-3" />
              {formatRelativeDate(job.published_at)}
            </span>
          )}
        </div>

        {job.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5" data-testid="job-card-tags">
            {job.tags.slice(0, 5).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-[11px] px-1.5 py-0">
                {tag}
              </Badge>
            ))}
            {job.tags.length > 5 && (
              <Badge variant="ghost" className="text-[11px] px-1.5 py-0 text-muted-foreground">
                +{job.tags.length - 5}
              </Badge>
            )}
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-0 justify-between">
        <Badge
          variant="outline"
          className={`text-[11px] border-0 ${SOURCE_COLORS[job.source] ?? "bg-secondary text-secondary-foreground"}`}
          data-testid="job-card-source"
        >
          {getSourceLabel(job.source)}
        </Badge>

        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          data-testid="job-card-external"
          onClick={(e) => e.stopPropagation()}
        >
          <span>Original</span>
          <ExternalLink className="size-3" />
        </a>
      </CardFooter>
    </Card>
  );
}
