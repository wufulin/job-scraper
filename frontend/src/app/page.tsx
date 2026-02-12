import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Briefcase, Search, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div data-testid="home-page" className="flex flex-col items-center justify-center gap-8 py-20">
      <div className="flex flex-col items-center gap-4 text-center">
        <Briefcase className="h-12 w-12 text-primary" />
        <h1 data-testid="hero-title" className="text-4xl font-bold tracking-tight">
          Job Scraper
        </h1>
        <p data-testid="hero-description" className="max-w-md text-lg text-muted-foreground">
          Aggregated remote AI, ML, and LLM job postings from multiple sources
          with smart keyword matching and cross-site deduplication.
        </p>
      </div>

      <div className="flex gap-3">
        <Link href="/jobs">
          <Button size="lg" data-testid="browse-jobs-button">
            <Search className="mr-2 h-4 w-4" />
            Browse Jobs
          </Button>
        </Link>
        <Link href="/dashboard">
          <Button variant="outline" size="lg" data-testid="dashboard-button">
            <Zap className="mr-2 h-4 w-4" />
            Dashboard
          </Button>
        </Link>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <FeatureCard
          title="Multi-Source"
          description="Jobs from RemoteOK, Eleduck, WeWorkRemotely, V2EX, Arc.dev, and more."
        />
        <FeatureCard
          title="Smart Filtering"
          description="Keyword matching with CJK support and cross-site deduplication."
        />
        <FeatureCard
          title="Always Fresh"
          description="Automated scraping keeps listings up to date."
        />
      </div>
    </div>
  );
}

function FeatureCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <h3 className="mb-2 font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
