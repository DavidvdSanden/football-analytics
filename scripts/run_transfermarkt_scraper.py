from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"


def _load_transfermarkt_module_from_src():
    module_path = SRC_PATH / "football_analytics" / "scrapers" / "transfermarkt.py"
    module_name = "transfermarkt_src_runtime"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load transfermarkt module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


transfermarkt_module = _load_transfermarkt_module_from_src()
TransfermarktConfig = transfermarkt_module.TransfermarktConfig
TransfermarktScraper = transfermarkt_module.TransfermarktScraper

# Central place for script-level tuning without changing CLI flags.
# Set values to None to keep existing environment/default behavior.
SCRIPT_RUNTIME_OVERRIDES: dict[str, str | bool | None] = {
    "TRANSFERMARKT_TRANSFERS_SPLIT_BY_CITIZENSHIP": True,
    "TRANSFERMARKT_MIN_MARKTWERT": "100000",
}


def apply_script_runtime_overrides() -> None:
    for env_key, value in SCRIPT_RUNTIME_OVERRIDES.items():
        if value is None:
            continue
        if isinstance(value, bool):
            os.environ[env_key] = "true" if value else "false"
        else:
            os.environ[env_key] = str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Transfermarkt market value changes and latest transfers "
            "and upsert into PostgreSQL."
        )
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

    # Apply script defaults first; explicit CLI args below still take precedence.
    apply_script_runtime_overrides()

    print(f"Using transfermarkt module: {transfermarkt_module.__file__}")

    if args.max_pages is not None:
        os.environ["TRANSFERMARKT_MAX_PAGES"] = args.max_pages
    if args.dry_run:
        os.environ["TRANSFERMARKT_DRY_RUN"] = "true"

    started_at = datetime.now(UTC)
    scraper = TransfermarktScraper(config=TransfermarktConfig())
    summary = scraper.scrape()
    finished_at = datetime.now(UTC)

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
