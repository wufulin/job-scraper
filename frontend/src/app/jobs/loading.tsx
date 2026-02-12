import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";

function JobCardSkeleton() {
  return (
    <Card data-testid="job-skeleton">
      <CardHeader className="pb-0 gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3.5 w-1/3" />
          </div>
          <Skeleton className="size-6 rounded-md shrink-0" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div className="flex gap-3">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-14" />
        </div>
        <div className="flex gap-1.5">
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
      </CardContent>
      <CardFooter className="pt-0 justify-between">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-3 w-14" />
      </CardFooter>
    </Card>
  );
}

export default function JobsLoading() {
  return (
    <div className="flex flex-col gap-6 px-4 py-8 mx-auto max-w-5xl w-full">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-80" />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Skeleton className="h-9 flex-1" />
        <Skeleton className="h-9 w-[160px]" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
