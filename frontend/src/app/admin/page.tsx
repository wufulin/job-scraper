"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth-context";
import { SitesTab } from "@/components/admin/SitesTab";
import { KeywordsTab } from "@/components/admin/KeywordsTab";
import { ScraperTab } from "@/components/admin/ScraperTab";
import { Shield, ShieldOff, Loader2, Server, Tags, Zap } from "lucide-react";

export default function AdminPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div
        data-testid="admin-loading"
        className="flex items-center justify-center py-20"
      >
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const role = user?.user_metadata?.role as string | undefined;
  const isAdmin = role === "admin";

  if (!user || !isAdmin) {
    return (
      <div data-testid="admin-denied" className="flex flex-col items-center gap-4 py-20">
        <ShieldOff className="h-12 w-12 text-muted-foreground" />
        <h1 className="text-2xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground max-w-md text-center">
          You don&apos;t have permission to access the admin console.
          Contact an administrator if you believe this is an error.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="admin-page" className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Console</h1>
          <p className="text-muted-foreground">
            Manage scraper configuration, keywords, and scheduling.
          </p>
        </div>
      </div>

      <Tabs defaultValue="sites" data-testid="admin-tabs">
        <TabsList>
          <TabsTrigger value="sites" data-testid="admin-tab-sites">
            <Server className="mr-1.5 h-4 w-4" />
            Sites
          </TabsTrigger>
          <TabsTrigger value="keywords" data-testid="admin-tab-keywords">
            <Tags className="mr-1.5 h-4 w-4" />
            Keywords
          </TabsTrigger>
          <TabsTrigger value="scraper" data-testid="admin-tab-scraper">
            <Zap className="mr-1.5 h-4 w-4" />
            Scraper
          </TabsTrigger>
        </TabsList>

        <TabsContent value="sites" className="mt-4">
          <SitesTab />
        </TabsContent>

        <TabsContent value="keywords" className="mt-4">
          <KeywordsTab />
        </TabsContent>

        <TabsContent value="scraper" className="mt-4">
          <ScraperTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
