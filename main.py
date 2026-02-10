#!/usr/bin/env python3
"""CLI entry point for the job scraper."""

from __future__ import annotations

import argparse
import signal
import sys

from scraper.logger import setup_logger
from scraper.orchestrator import ScraperOrchestrator


# Global orchestrator reference for signal handler
_orchestrator: ScraperOrchestrator | None = None


def _handle_sigint(signum: int, frame: object) -> None:
    """Handle Ctrl+C: set interrupt flag so the scrape loop exits gracefully."""
    from loguru import logger

    logger.warning("Ctrl+C received — finishing current job and saving data…")
    if _orchestrator is not None:
        _orchestrator.interrupted = True
    else:
        # No orchestrator yet, just exit
        sys.exit(130)


# ------------------------------------------------------------------
# Subcommand handlers
# ------------------------------------------------------------------


def cmd_scrape(args: argparse.Namespace) -> None:
    """Run the scraping pipeline."""
    global _orchestrator  # noqa: PLW0603

    from loguru import logger

    _orchestrator = ScraperOrchestrator()

    # Register signal handler *after* orchestrator exists
    signal.signal(signal.SIGINT, _handle_sigint)

    logger.info("Starting scrape command")
    summary = _orchestrator.run(site=args.site, dry_run=args.dry_run)

    # Print summary
    print("\n" + "=" * 50)
    print("  Scrape Summary")
    print("=" * 50)
    print(f"  Total fetched : {summary['total_scraped']}")
    print(f"  Matched       : {summary['matched']}")
    if not args.dry_run:
        print(f"  New jobs saved : {summary['new']}")
        print(f"  Updated        : {summary['updated']}")
    else:
        print("  (dry-run — nothing saved)")
    if summary["errors"]:
        print(f"  Errors         : {len(summary['errors'])}")
        for err in summary["errors"]:
            print(f"    - {err}")
    print("=" * 50)

    if _orchestrator.interrupted:
        print("\n  ⚠ Interrupted — partial results above")


def cmd_export(args: argparse.Namespace) -> None:
    """Export jobs to file."""
    from loguru import logger
    from scraper.utils.storage import StorageManager

    fmt = args.format
    output = args.output

    if fmt != "json":
        logger.error("Unsupported export format '{}'. Only 'json' is supported.", fmt)
        sys.exit(1)

    storage = StorageManager()
    logger.info("Exporting jobs to {}", output)
    storage.export_json(output)
    print(f"Exported jobs to {output}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show database statistics."""
    from scraper.utils.storage import StorageManager

    storage = StorageManager()
    stats = storage.get_stats()

    print("\n" + "=" * 50)
    print("  Database Statistics")
    print("=" * 50)
    print(f"  Total jobs  : {stats['total']}")
    print(f"  Active      : {stats['active']}")
    print(f"  Inactive    : {stats['inactive']}")
    if stats["by_source"]:
        print("  By source:")
        for source, count in sorted(stats["by_source"].items()):
            print(f"    {source:20s} : {count}")
    else:
        print("  By source   : (no data)")
    print("=" * 50)


# ------------------------------------------------------------------
# CLI definition
# ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with scrape/export/stats subcommands."""
    parser = argparse.ArgumentParser(
        prog="job-scraper",
        description="Remote job scraper — fetch, filter, and store AI/ML remote jobs",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG) logging",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- scrape ---
    scrape_p = sub.add_parser("scrape", help="Fetch jobs from configured sites")
    scrape_p.add_argument(
        "--site", "-s",
        choices=["remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"],
        default=None,
        help="Scrape only this site",
    )
    scrape_p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Fetch and match but don't save to database",
    )

    # --- export ---
    export_p = sub.add_parser("export", help="Export jobs to file")
    export_p.add_argument(
        "--format", "-f",
        choices=["json"],
        default="json",
        help="Export format (default: json)",
    )
    export_p.add_argument(
        "--output", "-o",
        default="data/exports/jobs.json",
        help="Output file path (default: data/exports/jobs.json)",
    )

    # --- stats ---
    sub.add_parser("stats", help="Show database statistics")

    return parser


def main() -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure logging first
    setup_logger(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "scrape": cmd_scrape,
        "export": cmd_export,
        "stats": cmd_stats,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
