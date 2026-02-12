"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDebouncedCallback } from "use-debounce";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SOURCES = [
  { value: "all", label: "All Sources" },
  { value: "remoteok", label: "RemoteOK" },
  { value: "eleduck", label: "Eleduck" },
  { value: "weworkremotely", label: "WWR" },
  { value: "v2ex", label: "V2EX" },
  { value: "arcdev", label: "Arc.dev" },
  { value: "workgo", label: "WorkGo" },
];

export function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const currentQuery = searchParams.get("q") ?? "";
  const currentSource = searchParams.get("source") ?? "all";

  const [query, setQuery] = useState(currentQuery);

  useEffect(() => {
    setQuery(searchParams.get("q") ?? "");
  }, [searchParams]);

  const pushParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === "" || value === "all") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      }
      params.delete("page");
      startTransition(() => {
        router.push(`/jobs?${params.toString()}`);
      });
    },
    [router, searchParams, startTransition],
  );

  const debouncedSearch = useDebouncedCallback((value: string) => {
    pushParams({ q: value || null });
  }, 300);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };

  const handleSourceChange = (value: string) => {
    pushParams({ source: value === "all" ? null : value });
  };

  const hasFilters = currentQuery || currentSource !== "all";

  const clearFilters = () => {
    setQuery("");
    startTransition(() => {
      router.push("/jobs");
    });
  };

  return (
    <div
      data-testid="filter-bar"
      className="flex flex-col gap-3 sm:flex-row sm:items-center"
    >
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          data-testid="filter-search"
          placeholder="Search jobs..."
          value={query}
          onChange={handleSearchChange}
          className="pl-9"
        />
      </div>

      <Select
        value={currentSource}
        onValueChange={handleSourceChange}
        data-testid="filter-source"
      >
        <SelectTrigger
          data-testid="filter-source-trigger"
          className="w-full sm:w-[160px]"
        >
          <SelectValue placeholder="All Sources" />
        </SelectTrigger>
        <SelectContent>
          {SOURCES.map((s) => (
            <SelectItem
              key={s.value}
              value={s.value}
              data-testid={`filter-source-${s.value}`}
            >
              {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={clearFilters}
          data-testid="filter-clear"
          className="shrink-0"
        >
          <X className="size-4" />
          Clear
        </Button>
      )}
    </div>
  );
}
