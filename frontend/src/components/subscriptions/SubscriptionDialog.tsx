"use client";

import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { supabase } from "@/lib/supabase";
import { createSubscription, updateSubscription } from "@/lib/api";
import type { Subscription } from "@/lib/types";

const AVAILABLE_SOURCES = [
  { value: "remoteok", label: "RemoteOK" },
  { value: "eleduck", label: "Eleduck" },
  { value: "weworkremotely", label: "WeWorkRemotely" },
  { value: "v2ex", label: "V2EX" },
  { value: "arcdev", label: "Arc.dev" },
];

const subscriptionSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  keywords: z.string().min(1, "At least one keyword is required"),
  match_mode: z.enum(["any", "all"]),
});

type FormValues = z.infer<typeof subscriptionSchema>;

interface SubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscription?: Subscription | null;
  onSaved: () => void;
}

export function SubscriptionDialog({
  open,
  onOpenChange,
  subscription,
  onSaved,
}: SubscriptionDialogProps) {
  const isEditing = !!subscription;
  const [selectedSources, setSelectedSources] = useState<string[]>(
    subscription?.sources ?? [],
  );
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormValues>({
    resolver: zodResolver(subscriptionSchema),
    defaultValues: {
      name: subscription?.name ?? "",
      keywords: subscription?.keywords?.join(", ") ?? "",
      match_mode: (subscription?.match_mode as "any" | "all") ?? "any",
    },
  });

  const matchMode = watch("match_mode");

  const toggleSource = useCallback((source: string) => {
    setSelectedSources((prev) =>
      prev.includes(source)
        ? prev.filter((s) => s !== source)
        : [...prev, source],
    );
  }, []);

  const onSubmit = useCallback(
    async (values: FormValues) => {
      setSubmitting(true);
      setSubmitError(null);

      try {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;
        if (!token) return;

        const keywords = values.keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean);

        const payload = {
          name: values.name,
          keywords,
          match_mode: values.match_mode,
          sources: selectedSources.length > 0 ? selectedSources : undefined,
        };

        if (isEditing && subscription) {
          await updateSubscription(token, subscription.id, payload);
        } else {
          await createSubscription(token, payload);
        }

        reset();
        setSelectedSources([]);
        onOpenChange(false);
        onSaved();
      } catch {
        setSubmitError("Failed to save subscription");
      } finally {
        setSubmitting(false);
      }
    },
    [isEditing, subscription, selectedSources, reset, onOpenChange, onSaved],
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="subscription-dialog">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Edit Subscription" : "New Subscription"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update your subscription settings."
              : "Create a subscription to get notified about matching jobs."}
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
          data-testid="subscription-form"
        >
          <div className="space-y-2">
            <Label htmlFor="sub-name">Name</Label>
            <Input
              id="sub-name"
              data-testid="subscription-name-input"
              placeholder="e.g. AI Engineer roles"
              {...register("name")}
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="sub-keywords">Keywords (comma-separated)</Label>
            <Input
              id="sub-keywords"
              data-testid="subscription-keywords-input"
              placeholder="e.g. AI, machine learning, LLM"
              {...register("keywords")}
            />
            {errors.keywords && (
              <p className="text-xs text-destructive">
                {errors.keywords.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Match Mode</Label>
            <Select
              value={matchMode}
              onValueChange={(v) => setValue("match_mode", v as "any" | "all")}
            >
              <SelectTrigger data-testid="subscription-match-mode" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Match Any keyword</SelectItem>
                <SelectItem value="all">Match All keywords</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Sources (optional — leave empty for all)</Label>
            <div
              className="flex flex-wrap gap-2"
              data-testid="subscription-sources"
            >
              {AVAILABLE_SOURCES.map((src) => {
                const active = selectedSources.includes(src.value);
                return (
                  <button
                    key={src.value}
                    type="button"
                    data-testid={`source-toggle-${src.value}`}
                    onClick={() => toggleSource(src.value)}
                    className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                      active
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/40"
                    }`}
                  >
                    {src.label}
                  </button>
                );
              })}
            </div>
          </div>

          {submitError && (
            <p
              className="text-xs text-destructive"
              data-testid="subscription-error"
            >
              {submitError}
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              data-testid="subscription-submit"
            >
              {submitting
                ? "Saving..."
                : isEditing
                  ? "Update"
                  : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
