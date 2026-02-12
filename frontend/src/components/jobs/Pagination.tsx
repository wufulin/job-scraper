"use client";

import { useCallback, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PaginationProps {
  page: number;
  totalPages: number;
}

function buildPageNumbers(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | "ellipsis")[] = [1];

  if (current > 3) pages.push("ellipsis");

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);

  if (current < total - 2) pages.push("ellipsis");

  pages.push(total);
  return pages;
}

export function Pagination({ page, totalPages }: PaginationProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const goToPage = useCallback(
    (target: number) => {
      const params = new URLSearchParams(searchParams.toString());
      if (target <= 1) {
        params.delete("page");
      } else {
        params.set("page", String(target));
      }
      startTransition(() => {
        router.push(`/jobs?${params.toString()}`);
      });
    },
    [router, searchParams, startTransition],
  );

  if (totalPages <= 1) return null;

  const pageNumbers = buildPageNumbers(page, totalPages);

  return (
    <nav
      data-testid="pagination"
      aria-label="Pagination"
      className="flex items-center justify-center gap-1"
    >
      <Button
        variant="ghost"
        size="icon-sm"
        disabled={page <= 1 || isPending}
        onClick={() => goToPage(page - 1)}
        data-testid="pagination-prev"
        aria-label="Previous page"
      >
        <ChevronLeft className="size-4" />
      </Button>

      {pageNumbers.map((item, idx) =>
        item === "ellipsis" ? (
          <span
            key={`ellipsis-${idx}`}
            className="flex size-8 items-center justify-center text-muted-foreground"
          >
            <MoreHorizontal className="size-4" />
          </span>
        ) : (
          <Button
            key={item}
            variant={item === page ? "default" : "ghost"}
            size="icon-sm"
            disabled={isPending}
            onClick={() => goToPage(item)}
            data-testid={`pagination-page-${item}`}
            aria-label={`Page ${item}`}
            aria-current={item === page ? "page" : undefined}
          >
            {item}
          </Button>
        ),
      )}

      <Button
        variant="ghost"
        size="icon-sm"
        disabled={page >= totalPages || isPending}
        onClick={() => goToPage(page + 1)}
        data-testid="pagination-next"
        aria-label="Next page"
      >
        <ChevronRight className="size-4" />
      </Button>
    </nav>
  );
}
