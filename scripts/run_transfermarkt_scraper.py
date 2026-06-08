from __future__ import annotations

import argparse
import importlib.util
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
    config = TransfermarktConfig()
    scraper = TransfermarktScraper(config=config)
    summary = scraper.scrape()
    finished_at = datetime.now(UTC)
    duration = int((finished_at - started_at).total_seconds())

    _print_summary(summary, config, started_at, finished_at, duration, scraper.logger)
    return 0


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    return str(value)


def _row(label: str, value: object, indent: int = 2) -> str:
    pad = " " * indent
    return f"{pad}{label:<40} {_fmt(value)}"


def _section(title: str) -> str:
    return f"\n  {'─' * 50}\n  {title}\n  {'─' * 50}"


def _print_summary(
    summary: dict,
    config,
    started_at: datetime,
    finished_at: datetime,
    duration: int,
    logger=None,
) -> None:
    dry_run = os.getenv("TRANSFERMARKT_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    split_by_citizenship = config.latest_transfers_split_by_citizenship
    merge_enabled = config.merge_latest_transfers_on_identity
    only_new = config.upsert_only_new_values

    lines = []
    lines.append("")
    lines.append("  " + "═" * 50)
    lines.append("  TRANSFERMARKT SCRAPE SUMMARY")
    lines.append("  " + "═" * 50)

    # ── Run info ────────────────────────────────────────────────
    lines.append(_section("Run info"))
    lines.append(_row("Started", started_at.strftime("%Y-%m-%d %H:%M:%S UTC")))
    lines.append(_row("Finished", finished_at.strftime("%Y-%m-%d %H:%M:%S UTC")))
    lines.append(_row("Duration", f"{duration}s"))
    lines.append(_row("Dry run", "yes" if dry_run else "no"))
    lines.append(_row("Start URL", summary.get("selected_start_url", "-")))
    lines.append(_row("HTTP 429 responses", summary.get("http_429_count", 0)))

    # ── Market value changes ────────────────────────────────────
    lines.append(_section("Market value changes"))
    lines.append(_row("Pages scraped", summary.get("pages_processed", 0)))
    lines.append(_row("Rows parsed", summary.get("rows_parsed", 0)))
    lines.append(_row("clubs  upserted", summary.get("clubs_upserted", 0)))
    lines.append(_row("players  upserted", summary.get("players_upserted", 0)))
    lines.append(
        _row(
            "player_market_values  upserted",
            summary.get("player_market_values_upserted", 0),
        )
    )
    upsert_mode = "only new" if only_new else "all (upsert)"
    lines.append(_row("Upsert mode", upsert_mode))

    # ── Player / club profile enrichment ────────────────────────
    lines.append(_section("Profile enrichment"))
    lines.append(
        _row("Player profiles enriched", summary.get("player_profiles_enriched", 0))
    )
    lines.append(
        _row("Club profiles enriched", summary.get("club_profiles_enriched", 0))
    )

    # ── Latest transfers ────────────────────────────────────────
    lines.append(_section("Latest transfers"))
    split_label = "by citizenship" if split_by_citizenship else "global listing"
    lines.append(_row("Source split mode", split_label))
    lines.append(
        _row("Pages scraped", summary.get("latest_transfers_pages_processed", 0))
    )
    lines.append(_row("Rows parsed", summary.get("latest_transfers_rows_parsed", 0)))
    lines.append(
        _row("Total upserted (DB writes)", summary.get("latest_transfers_upserted", 0))
    )
    if merge_enabled:
        lines.append(
            _row("  — new rows inserted", summary.get("latest_transfers_new_rows", 0))
        )
        lines.append(
            _row(
                "  — existing rows enriched (merged)",
                summary.get("latest_transfers_merged_updates", 0),
            )
        )
        lines.append(
            _row(
                "  — unchanged (skipped)",
                summary.get("latest_transfers_unchanged_existing", 0),
            )
        )
    else:
        lines.append(_row("Merge-on-identity", "disabled"))

    lines.append("")
    lines.append("  " + "═" * 50)
    lines.append("")

    text = "\n".join(lines)
    if logger is not None:
        for line in lines:
            logger.info("%s", line)
    else:
        print(text)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Transfermarkt scraper failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
