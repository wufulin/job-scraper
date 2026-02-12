"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchSiteConfigs, updateSiteConfig } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { SiteConfig } from "@/lib/types";
import { Pencil, Server, AlertCircle } from "lucide-react";

export function SitesTab() {
  const [sites, setSites] = useState<SiteConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [editingSite, setEditingSite] = useState<SiteConfig | null>(null);
  const [editRateLimit, setEditRateLimit] = useState("");
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  const loadSites = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("Not authenticated");
      const data = await fetchSiteConfigs(token);
      setSites(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sites");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSites();
  }, [loadSites]);

  const handleToggle = async (site: SiteConfig) => {
    try {
      setUpdating(site.id);
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      const updated = await updateSiteConfig(token, site.id, {
        enabled: !site.enabled,
      });
      setSites((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch {
      setError("Failed to update site");
    } finally {
      setUpdating(null);
    }
  };

  const handleSaveRateLimit = async () => {
    if (!editingSite) return;
    const value = parseFloat(editRateLimit);
    if (isNaN(value) || value < 0) return;
    try {
      setUpdating(editingSite.id);
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      const updated = await updateSiteConfig(token, editingSite.id, {
        rate_limit_seconds: value,
      });
      setSites((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      setEditDialogOpen(false);
      setEditingSite(null);
    } catch {
      setError("Failed to update rate limit");
    } finally {
      setUpdating(null);
    }
  };

  const openEditDialog = (site: SiteConfig) => {
    setEditingSite(site);
    setEditRateLimit(String(site.rate_limit_seconds));
    setEditDialogOpen(true);
  };

  if (loading) {
    return (
      <Card data-testid="sites-tab">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Site Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="sites-tab">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Site Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex items-center gap-2 text-destructive"
            data-testid="sites-error"
          >
            <AlertCircle className="h-4 w-4" />
            <p className="text-sm">{error}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={loadSites}
            data-testid="sites-retry"
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="sites-tab">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="h-5 w-5" />
          Site Configuration
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Adapter</TableHead>
              <TableHead>Enabled</TableHead>
              <TableHead>Rate Limit</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sites.map((site) => (
              <TableRow key={site.id} data-testid="site-row">
                <TableCell className="font-medium" data-testid="site-name">
                  {site.name}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" data-testid="site-adapter">
                    {site.adapter}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Switch
                    checked={site.enabled}
                    onCheckedChange={() => handleToggle(site)}
                    disabled={updating === site.id}
                    data-testid="site-toggle"
                  />
                </TableCell>
                <TableCell data-testid="site-rate-limit">
                  {site.rate_limit_seconds}s
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEditDialog(site)}
                    data-testid="site-edit-btn"
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent data-testid="site-edit-dialog">
            <DialogHeader>
              <DialogTitle>
                Edit {editingSite?.name ?? "Site"}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="rate-limit">Rate Limit (seconds)</Label>
                <Input
                  id="rate-limit"
                  type="number"
                  min={0}
                  step={0.5}
                  value={editRateLimit}
                  onChange={(e) => setEditRateLimit(e.target.value)}
                  data-testid="site-rate-limit-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveRateLimit}
                disabled={updating !== null}
                data-testid="site-save-btn"
              >
                Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
