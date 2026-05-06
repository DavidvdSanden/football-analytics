from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

from football_analytics.scrapers.transfermarkt import TransfermarktConfig, TransfermarktScraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Transfermarkt market value changes and upsert into PostgreSQL."
    )
    parser.add_argument(
        "--max-pages",
        type=str,
        default=None,
        help='Max pages to scrape (integer or "all"). Overrides TRANSFERMARKT_MAX_PAGES.',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse pages without writing to the database.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.max_pages is not None:
        os.environ["TRANSFERMARKT_MAX_PAGES"] = args.max_pages
    if args.dry_run:
        os.environ["TRANSFERMARKT_DRY_RUN"] = "true"

    started_at = datetime.utcnow()
    scraper = TransfermarktScraper(config=TransfermarktConfig())
    summary = scraper.scrape()
    finished_at = datetime.utcnow()

    summary["started_at_utc"] = started_at.isoformat(timespec="seconds")
    summary["finished_at_utc"] = finished_at.isoformat(timespec="seconds")
    summary["duration_seconds"] = int((finished_at - started_at).total_seconds())

    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Transfermarkt scraper failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
