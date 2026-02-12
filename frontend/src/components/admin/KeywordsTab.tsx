"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchKeywordConfigs,
  createKeyword,
  updateKeyword,
  deleteKeyword,
} from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { KeywordConfig } from "@/lib/types";
import { Tags, Plus, Trash2, AlertCircle } from "lucide-react";

export function KeywordsTab() {
  const [keywords, setKeywords] = useState<KeywordConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<number | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<KeywordConfig | null>(null);
  const [newKeyword, setNewKeyword] = useState("");
  const [newGroup, setNewGroup] = useState("");

  const loadKeywords = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("Not authenticated");
      const data = await fetchKeywordConfigs(token);
      setKeywords(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load keywords",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadKeywords();
  }, [loadKeywords]);

  const groupNames = useMemo(() => {
    const names = new Set(keywords.map((k) => k.group_name));
    return Array.from(names).sort();
  }, [keywords]);

  const groupedKeywords = useMemo(() => {
    const groups: Record<string, KeywordConfig[]> = {};
    for (const kw of keywords) {
      if (!groups[kw.group_name]) groups[kw.group_name] = [];
      groups[kw.group_name].push(kw);
    }
    return groups;
  }, [keywords]);

  const handleToggle = async (kw: KeywordConfig) => {
    try {
      setUpdating(kw.id);
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      const updated = await updateKeyword(token, kw.id, {
        enabled: !kw.enabled,
      });
      setKeywords((prev) =>
        prev.map((k) => (k.id === updated.id ? updated : k)),
      );
    } catch {
      setError("Failed to update keyword");
    } finally {
      setUpdating(null);
    }
  };

  const handleAdd = async () => {
    if (!newKeyword.trim() || !newGroup.trim()) return;
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      const created = await createKeyword(token, {
        group_name: newGroup.trim(),
        keyword: newKeyword.trim(),
      });
      setKeywords((prev) => [...prev, created]);
      setNewKeyword("");
      setNewGroup("");
      setAddDialogOpen(false);
    } catch {
      setError("Failed to add keyword");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      setUpdating(deleteTarget.id);
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;
      await deleteKeyword(token, deleteTarget.id);
      setKeywords((prev) => prev.filter((k) => k.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      setError("Failed to delete keyword");
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <Card data-testid="keywords-tab">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Tags className="h-5 w-5" />
            Keyword Configuration
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

  if (error && keywords.length === 0) {
    return (
      <Card data-testid="keywords-tab">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Tags className="h-5 w-5" />
            Keyword Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex items-center gap-2 text-destructive"
            data-testid="keywords-error"
          >
            <AlertCircle className="h-4 w-4" />
            <p className="text-sm">{error}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={loadKeywords}
            data-testid="keywords-retry"
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="keywords-tab">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Tags className="h-5 w-5" />
          Keyword Configuration
        </CardTitle>
        <Button
          size="sm"
          onClick={() => setAddDialogOpen(true)}
          data-testid="keyword-add-btn"
        >
          <Plus className="mr-1 h-4 w-4" />
          Add Keyword
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <div
            className="flex items-center gap-2 text-destructive text-sm"
            data-testid="keywords-error"
          >
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {groupNames.map((group) => (
          <div key={group} data-testid="keyword-group">
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="secondary" data-testid="keyword-group-name">
                {group}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {groupedKeywords[group].length} keywords
              </span>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Keyword</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groupedKeywords[group].map((kw) => (
                  <TableRow key={kw.id} data-testid="keyword-row">
                    <TableCell
                      className="font-medium"
                      data-testid="keyword-value"
                    >
                      {kw.keyword}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={kw.enabled}
                        onCheckedChange={() => handleToggle(kw)}
                        disabled={updating === kw.id}
                        data-testid="keyword-toggle"
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeleteTarget(kw)}
                        data-testid="keyword-delete-btn"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ))}

        <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
          <DialogContent data-testid="keyword-add-dialog">
            <DialogHeader>
              <DialogTitle>Add Keyword</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="kw-group">Group</Label>
                <Select value={newGroup} onValueChange={setNewGroup}>
                  <SelectTrigger data-testid="keyword-group-select">
                    <SelectValue placeholder="Select group" />
                  </SelectTrigger>
                  <SelectContent>
                    {groupNames.map((g) => (
                      <SelectItem key={g} value={g}>
                        {g}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Or type new group name"
                  value={groupNames.includes(newGroup) ? "" : newGroup}
                  onChange={(e) => setNewGroup(e.target.value)}
                  data-testid="keyword-group-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="kw-value">Keyword</Label>
                <Input
                  id="kw-value"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  placeholder="e.g. machine learning"
                  data-testid="keyword-value-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setAddDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAdd}
                disabled={!newKeyword.trim() || !newGroup.trim()}
                data-testid="keyword-save-btn"
              >
                Add
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog
          open={deleteTarget !== null}
          onOpenChange={(open) => !open && setDeleteTarget(null)}
        >
          <DialogContent data-testid="keyword-delete-dialog">
            <DialogHeader>
              <DialogTitle>Delete Keyword</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete{" "}
              <strong>&ldquo;{deleteTarget?.keyword}&rdquo;</strong> from the{" "}
              <strong>{deleteTarget?.group_name}</strong> group? This action
              cannot be undone.
            </p>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={updating !== null}
                data-testid="keyword-confirm-delete-btn"
              >
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
