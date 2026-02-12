import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

export default function JobDetailLoading() {
  return (
    <div
      data-testid="job-detail-loading"
      className="mx-auto max-w-4xl space-y-6"
    >
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-24" />
      </div>

      <Card>
        <CardHeader className="space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-4 w-16" />
          </div>
          <Skeleton className="h-9 w-3/4" />
          <div className="flex gap-1.5">
            <Skeleton className="h-5 w-14" />
            <Skeleton className="h-5 w-18" />
            <Skeleton className="h-5 w-12" />
          </div>
        </CardHeader>

        <Separator />

        <CardContent className="pt-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3">
                <Skeleton className="size-9 shrink-0 rounded-lg" />
                <div className="space-y-1.5 flex-1">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-4 w-28" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-36" />
        </CardHeader>
        <Separator />
        <CardContent className="pt-6 space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="py-4">
          <div className="flex gap-6">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-4 w-36" />
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Skeleton className="h-11 flex-1" />
        <Skeleton className="h-11 w-full sm:w-36" />
      </div>
    </div>
  );
}
