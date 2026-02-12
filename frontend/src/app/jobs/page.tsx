import { Suspense } from "react";
import { Briefcase, SearchX } from "lucide-react";
import { fetchJobs } from "@/lib/api";
import type { JobListResponse } from "@/lib/types";
import { JobCard } from "@/components/jobs/JobCard";
import { FilterBar } from "@/components/jobs/FilterBar";
import { Pagination } from "@/components/jobs/Pagination";
import JobsLoading from "./loading";

interface JobsPageProps {
  searchParams: Promise<{
    page?: string;
    per_page?: string;
    q?: string;
    source?: string;
  }>;
}

async function JobList({
  page,
  perPage,
  search,
  source,
}: {
  page: number;
  perPage: number;
  search?: string;
  source?: string;
}) {
  let data: JobListResponse;

  try {
    data = await fetchJobs({
      page,
      per_page: perPage,
      search: search || undefined,
      source: source || undefined,
    });
  } catch {
    return (
      <div
        data-testid="jobs-error"
        className="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <div className="rounded-full bg-destructive/10 p-3">
          <SearchX className="size-6 text-destructive" />
        </div>
        <p className="text-sm font-medium">Failed to load jobs</p>
        <p className="text-xs text-muted-foreground max-w-sm">
          The API might be unavailable. Check that the backend is running and try again.
        </p>
      </div>
    );
  }

  if (data.data.length === 0) {
    return (
      <div
        data-testid="jobs-empty"
        className="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <div className="rounded-full bg-muted p-3">
          <Briefcase className="size-6 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium">No jobs found</p>
        <p className="text-xs text-muted-foreground max-w-sm">
          {search
            ? `No results for "${search}". Try a different search term.`
            : "No job listings available. Try adjusting your filters."}
        </p>
      </div>
    );
  }

  return (
    <>
      <p className="text-sm text-muted-foreground" data-testid="jobs-count">
        {data.pagination.total} job{data.pagination.total !== 1 ? "s" : ""} found
      </p>

      <div className="grid gap-4 sm:grid-cols-2" data-testid="jobs-grid">
        {data.data.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>

      <Pagination page={data.pagination.page} totalPages={data.pagination.total_pages} />
    </>
  );
}

export default async function JobsPage({ searchParams }: JobsPageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const perPage = Math.min(50, Math.max(1, Number(params.per_page) || 20));
  const search = params.q ?? "";
  const source = params.source ?? "";

  return (
    <div
      data-testid="jobs-page"
      className="flex flex-col gap-6 px-4 py-8 mx-auto max-w-5xl w-full"
    >
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>
        <p className="text-muted-foreground">
          Browse remote AI/ML job listings from multiple sources.
        </p>
      </div>

      <FilterBar />

      <Suspense fallback={<JobsLoading />}>
        <JobList page={page} perPage={perPage} search={search} source={source} />
      </Suspense>
    </div>
  );
}
