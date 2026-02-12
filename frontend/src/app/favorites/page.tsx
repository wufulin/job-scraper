"use client";

import { useCallback, useEffect, useState } from "react";
import { Heart, Loader2, HeartOff } from "lucide-react";
import { useRequireAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { fetchFavorites, fetchJob, removeFavorite } from "@/lib/api";
import { JobCard } from "@/components/jobs/JobCard";
import { Skeleton } from "@/components/ui/skeleton";
import type { Job } from "@/lib/types";

export default function FavoritesPage() {
  const { user, authenticated } = useRequireAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [favoriteJobIds, setFavoriteJobIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFavorites = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      const favRes = await fetchFavorites(token);
      const jobIds = favRes.data.map((f) => f.job_id);
      setFavoriteJobIds(new Set(jobIds));

      const jobResults = await Promise.all(
        jobIds.map((id) => fetchJob(id).catch(() => null)),
      );
      setJobs(jobResults.filter((j): j is Job => j !== null));
    } catch {
      setError("Failed to load favorites");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authenticated) loadFavorites();
  }, [authenticated, loadFavorites]);

  const handleRemoveFavorite = useCallback(
    async (jobId: string) => {
      const prevJobs = jobs;
      const prevIds = favoriteJobIds;
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      setFavoriteJobIds((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;
        await removeFavorite(token, jobId);
      } catch {
        setJobs(prevJobs);
        setFavoriteJobIds(prevIds);
      }
    },
    [jobs, favoriteJobIds],
  );

  const handleFavoriteChange = useCallback(
    (jobId: string, favorited: boolean) => {
      if (!favorited) handleRemoveFavorite(jobId);
    },
    [handleRemoveFavorite],
  );

  return (
    <div
      data-testid="favorites-page"
      className="flex flex-col gap-6 px-4 py-8 mx-auto max-w-5xl w-full"
    >
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight">Favorites</h1>
        <p className="text-muted-foreground">
          Jobs you&apos;ve saved for later.
        </p>
      </div>

      {loading && (
        <div data-testid="favorites-loading" className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      )}

      {!loading && error && (
        <div
          data-testid="favorites-error"
          className="flex flex-col items-center justify-center gap-3 py-16 text-center"
        >
          <div className="rounded-full bg-destructive/10 p-3">
            <Loader2 className="size-6 text-destructive" />
          </div>
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div
          data-testid="favorites-empty"
          className="flex flex-col items-center justify-center gap-3 py-16 text-center"
        >
          <div className="rounded-full bg-muted p-3">
            <HeartOff className="size-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium">No favorites yet</p>
          <p className="text-xs text-muted-foreground max-w-sm">
            Click the heart icon on any job card to save it here.
          </p>
        </div>
      )}

      {!loading && !error && jobs.length > 0 && (
        <>
          <p className="text-sm text-muted-foreground" data-testid="favorites-count">
            {jobs.length} favorite{jobs.length !== 1 ? "s" : ""}
          </p>
          <div className="grid gap-4 sm:grid-cols-2" data-testid="favorites-grid">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isFavorited={favoriteJobIds.has(job.id)}
                onFavoriteChange={handleFavoriteChange}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
