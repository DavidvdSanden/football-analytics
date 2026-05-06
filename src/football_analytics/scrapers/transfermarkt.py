from __future__ import annotations

import hashlib
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from football_analytics.utils.database import upsert_rows
from football_analytics.utils.db_schema import ensure_transfermarkt_tables


def _env_bool(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class TransfermarktConfig:
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "TRANSFERMARKT_BASE_URL",
            "https://www.transfermarkt.com/spieler-statistik/marktwertaenderungen/marktwertetop",
        )
    )
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "TRANSFERMARKT_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
    )
    accept_language: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_ACCEPT_LANGUAGE", "en-US,en;q=0.9")
    )
    referer_url: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_REFERER", "https://www.transfermarkt.com/")
    )
    min_delay_seconds: float = field(
        default_factory=lambda: float(os.getenv("TRANSFERMARKT_MIN_DELAY", "2.0"))
    )
    max_delay_seconds: float = field(
        default_factory=lambda: float(os.getenv("TRANSFERMARKT_MAX_DELAY", "4.0"))
    )
    timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("TRANSFERMARKT_TIMEOUT", "30"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("TRANSFERMARKT_RETRY_MAX", "5"))
    )
    backoff_base_seconds: float = field(
        default_factory=lambda: float(os.getenv("TRANSFERMARKT_BACKOFF_BASE", "1.0"))
    )
    max_pages: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_MAX_PAGES", "all")
    )
    batch_size: int = field(
        default_factory=lambda: int(os.getenv("TRANSFERMARKT_BATCH_SIZE", "200"))
    )
    max_429_before_stop: int = field(
        default_factory=lambda: int(os.getenv("TRANSFERMARKT_429_CIRCUIT_BREAKER", "20"))
    )
    dry_run: bool = field(default_factory=lambda: _env_bool("TRANSFERMARKT_DRY_RUN", False))
    db_schema: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_DB_SCHEMA", "transfermarkt")
    )
    fallback_start_urls: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_FALLBACK_START_URLS", "")
    )

    def max_pages_int(self) -> int | None:
        value = self.max_pages.strip().lower()
        if value == "all":
            return None
        return max(int(value), 1)


class TransfermarktScraper:
    """Scrape Transfermarkt market value changes with ethical request pacing."""

    def __init__(self, config: TransfermarktConfig | None = None, logger: logging.Logger | None = None):
        self.config = config or TransfermarktConfig()
        self.session = self._create_session()
        self._last_request_ts: float | None = None
        self._count_429 = 0
        self._did_warmup = False
        self._selected_start_url: str | None = None
        self.logger = logger or self._build_logger()

    def _create_session(self, referer_url: str | None = None) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": self.config.accept_language,
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": referer_url or self.config.referer_url,
            }
        )
        return session

    def _reset_session(self, referer_url: str | None = None) -> None:
        try:
            self.session.close()
        except Exception:
            pass
        self.session = self._create_session(referer_url=referer_url)
        self._did_warmup = False

    def _build_start_url_candidates(self) -> list[str]:
        candidates = [self.config.base_url]

        if not self.config.base_url.endswith("/"):
            candidates.append(f"{self.config.base_url}/")

        # The filtered URL variant often avoids unstable responses on the default landing page.
        candidates.append(
            "https://www.transfermarkt.com/spieler-statistik/marktwertaenderungen/"
            "marktwertetop/?plus=1&galerie=0&position=alle&spielerposition_id=0&"
            "spieler_land_id=0&verein_land_id=&wettbewerb_id=alle&alter=16+-+45&"
            "filtern_nach_alter=16%3B45&minAlter=16&maxAlter=45&minMarktwert=100.000&"
            "maxMarktwert=200.000.000&yt0=Show"
        )

        if self.config.fallback_start_urls.strip():
            env_urls = [u.strip() for u in self.config.fallback_start_urls.split(",") if u.strip()]
            candidates.extend(env_urls)

        unique: list[str] = []
        for url in candidates:
            if url not in unique:
                unique.append(url)
        return unique

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("transfermarkt_scraper")
        if logger.handlers:
            return logger

        logger.setLevel(logging.INFO)
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"transfermarkt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        return logger

    def _wait_for_rate_limit(self) -> None:
        now = time.monotonic()
        if self._last_request_ts is None:
            self._last_request_ts = now
            return

        target_delay = random.uniform(
            self.config.min_delay_seconds,
            max(self.config.max_delay_seconds, self.config.min_delay_seconds),
        )
        elapsed = now - self._last_request_ts
        wait_time = max(0.0, target_delay - elapsed)
        if wait_time > 0:
            time.sleep(wait_time)
        self._last_request_ts = time.monotonic()

    def _request_with_retries(
        self,
        url: str,
        page_num: int,
        referer_url: str | None = None,
    ) -> requests.Response:
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            self._wait_for_rate_limit()
            try:
                if page_num > 1 and attempt == 1:
                    self._reset_session(referer_url=referer_url or self.config.referer_url)

                if not self._did_warmup:
                    warmup_url = self.config.referer_url
                    if page_num == 1:
                        self.session.get(
                            warmup_url,
                            timeout=self.config.timeout_seconds,
                        )
                    self._did_warmup = True

                response = self.session.get(
                    url,
                    timeout=self.config.timeout_seconds,
                )
                if response.status_code == 429:
                    self._count_429 += 1
                    if self._count_429 >= self.config.max_429_before_stop:
                        raise RuntimeError(
                            "Stopped scraping after repeated HTTP 429 responses."
                        )
                    backoff = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                    self.logger.warning(
                        "HTTP 429 on page %s (attempt %s/%s). Backing off %.1fs.",
                        page_num,
                        attempt,
                        self.config.max_retries,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue

                response.raise_for_status()
                self.session.headers["Referer"] = response.url
                return response
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                last_error = exc
                backoff = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if isinstance(exc, requests.Timeout) or (status_code is not None and status_code >= 500):
                    self._reset_session(
                        referer_url=referer_url or self.config.referer_url
                    )
                self.logger.warning(
                    "Request failed for page %s (attempt %s/%s): %s. Retrying in %.1fs.",
                    page_num,
                    attempt,
                    self.config.max_retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(f"Failed to fetch page {page_num} after retries") from last_error

    def _request_first_page(self, page_num: int) -> requests.Response:
        candidates = self._build_start_url_candidates()
        last_error: Exception | None = None

        for idx, candidate in enumerate(candidates, start=1):
            try:
                if idx > 1:
                    self.logger.warning(
                        "Trying fallback start URL %s/%s: %s",
                        idx,
                        len(candidates),
                        candidate,
                    )
                response = self._request_with_retries(
                    candidate,
                    page_num,
                    referer_url=self.config.referer_url,
                )
                self._selected_start_url = candidate
                return response
            except RuntimeError as exc:
                last_error = exc
                continue

        raise RuntimeError("Failed to fetch first page from all start URL candidates") from last_error

    @staticmethod
    def _extract_tm_id(href: str | None) -> str | None:
        if not href:
            return None
        match = re.search(r"/(\d+)(?:$|[/?#])", href)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _to_int(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fallback_tm_id(prefix: str, raw_name: str | None) -> str:
        value = (raw_name or "unknown").strip().lower()
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"

    @staticmethod
    def _parse_age(value: str) -> int | None:
        digits = re.findall(r"\d+", value or "")
        if not digits:
            return None
        return int(digits[0])

    @staticmethod
    def _parse_changed_on(value: str) -> date | None:
        text = (value or "").strip()
        for fmt in ("%b %d, %Y", "%b %d, %y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_market_value_eur(value: str | None) -> int | None:
        if not value:
            return None
        text = value.strip().replace("€", "").replace(",", ".").lower()
        text = text.replace("+", "").replace("-", "")
        multiplier = 1
        if text.endswith("bn"):
            multiplier = 1_000_000_000
            text = text[:-2]
        elif text.endswith("m"):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith("k"):
            multiplier = 1_000
            text = text[:-1]

        text = text.strip()
        if not text or text == "-":
            return None
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return None

    @staticmethod
    def _extract_page_number(url_or_path: str | None) -> int | None:
        if not url_or_path:
            return None
        parsed = urlparse(url_or_path)
        page_value = parse_qs(parsed.query).get("page", [None])[0]
        if page_value is None:
            return None
        try:
            return int(page_value)
        except (TypeError, ValueError):
            return None

    def _parse_page(self, html: str, page: int) -> tuple[list[dict[str, Any]], str | None]:
        soup = BeautifulSoup(html, "lxml")
        table = (
            soup.select_one("table.items")
            or soup.select_one(".box table.items")
            or soup.select_one("table[class*='items']")
            or soup.select_one(".items")
        )
        if table is None:
            self.logger.warning("No table.items found on page %s", page)
            title = soup.title.get_text(strip=True) if soup.title else "n/a"
            self.logger.warning("Unexpected HTML title on page %s: %s", page, title)
            return [], None

        rows: list[dict[str, Any]] = []
        for row in table.select("tr.odd, tr.even"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 6:
                continue

            player_inline = cells[0].select_one("table.inline-table")
            player_anchor = (
                player_inline.select_one("td.hauptlink a") if player_inline else None
            )
            player_name = player_anchor.get_text(strip=True) if player_anchor else None
            player_href = player_anchor.get("href") if player_anchor else None
            player_tm_id = self._extract_tm_id(player_href) or self._fallback_tm_id(
                "player", player_name
            )

            position = None
            if player_inline:
                trs = player_inline.select("tr")
                if len(trs) > 1:
                    position = trs[1].get_text(" ", strip=True)

            nationality = ", ".join(
                img.get("title") for img in cells[1].select("img") if img.get("title")
            ) or None
            age = self._parse_age(cells[2].get_text(strip=True))

            club_anchor = cells[3].select_one("a")
            club_name = None
            club_href = None
            if club_anchor:
                club_name = club_anchor.get("title") or club_anchor.get_text(strip=True)
                club_href = club_anchor.get("href")
            if not club_name:
                club_img = cells[3].select_one("img")
                if club_img:
                    club_name = club_img.get("title")
            club_tm_id = self._extract_tm_id(club_href) or self._fallback_tm_id(
                "club", club_name
            )

            if len(cells) >= 9:
                new_mv_raw = cells[4].get_text(" ", strip=True)
                old_mv_raw = cells[5].get_text(" ", strip=True)
                diff_raw = cells[6].get_text(" ", strip=True)
                percentage_raw = cells[7].get_text(" ", strip=True)
                changed_on_raw = cells[8].get_text(" ", strip=True)
            else:
                # Compact page variant has only current market value and date.
                new_mv_raw = cells[4].get_text(" ", strip=True)
                old_mv_raw = None
                diff_raw = None
                percentage_raw = None
                changed_on_raw = cells[5].get_text(" ", strip=True)

            percentage_value = None
            if percentage_raw:
                percentage_clean = (
                    percentage_raw.replace("%", "").replace(",", ".").strip()
                )
                try:
                    percentage_value = float(percentage_clean) if percentage_clean else None
                except ValueError:
                    percentage_value = None

            rows.append(
                {
                    "player_tm_id": player_tm_id,
                    "player_name": player_name,
                    "position": position,
                    "nationality": nationality,
                    "age": age,
                    "club_tm_id": club_tm_id,
                    "club_name": club_name,
                    "player_profile_url": make_transfermarkt_full_url(player_href)
                    if player_href
                    else None,
                    "club_profile_url": make_transfermarkt_full_url(club_href)
                    if club_href
                    else None,
                    "new_market_value_raw": new_mv_raw,
                    "old_market_value_raw": old_mv_raw,
                    "difference_raw": diff_raw,
                    "percentage_change": percentage_value,
                    "changed_on": self._parse_changed_on(changed_on_raw),
                }
            )

        next_url = None

        next_link = soup.select_one("a.tm-pagination__link--icon-next") or soup.select_one(
            "a[rel='next']"
        )
        if next_link and next_link.get("href"):
            next_url = make_transfermarkt_full_url(next_link.get("href"))
        else:
            # Fallback: parse numbered pagination links and select the smallest page > current.
            page_links: list[tuple[int, str]] = []
            for anchor in soup.select(".tm-pagination a, div.tm-pagination a, ul.tm-pagination a"):
                href = anchor.get("href")
                page_num = self._extract_page_number(href)
                if href and page_num is not None and page_num > page:
                    page_links.append((page_num, href))

            if page_links:
                next_href = min(page_links, key=lambda x: x[0])[1]
                next_url = make_transfermarkt_full_url(next_href)

        return rows, next_url

    def _table(self, table_name: str) -> str:
        return f"{self.config.db_schema}.{table_name}"

    def _persist_rows(self, parsed_rows: list[dict[str, Any]]) -> dict[str, int]:
        if not parsed_rows:
            return {"clubs": 0, "players": 0, "player_market_values": 0}

        clubs_map: dict[str, dict[str, Any]] = {}
        players_map: dict[str, dict[str, Any]] = {}
        for item in parsed_rows:
            club_id = self._to_int(item["club_tm_id"])
            player_id = self._to_int(item["player_tm_id"])
            if club_id is None or player_id is None:
                continue

            clubs_map[item["club_tm_id"]] = {
                "tm_club_id": club_id,
                "club_name": item["club_name"] or "Unknown Club",
                "country": None,
                "profile_url": item.get("club_profile_url"),
                "scraped_at": datetime.utcnow().replace(microsecond=0),
            }
            players_map[item["player_tm_id"]] = {
                "tm_player_id": player_id,
                "full_name": item["player_name"] or "Unknown Player",
                "main_position": item["position"],
                "nationality": item["nationality"],
                "date_of_birth": None,
                "preferred_foot": None,
                "current_tm_club_id": str(club_id),
                "profile_url": item.get("player_profile_url"),
                "scraped_at": datetime.utcnow().replace(microsecond=0),
                "updated_at": datetime.utcnow().replace(microsecond=0),
            }

        clubs = list(clubs_map.values())
        players = list(players_map.values())

        upsert_rows(self._table("clubs"), clubs, conflict_columns="tm_club_id")
        upsert_rows(self._table("players"), players, conflict_columns="tm_player_id")

        market_rows: list[dict[str, Any]] = []
        scrape_date = datetime.utcnow().replace(microsecond=0)

        for item in parsed_rows:
            player_id = self._to_int(item["player_tm_id"])
            if player_id is None:
                continue
            valuation_date = item["changed_on"] or datetime.utcnow().date()

            market_rows.append(
                {
                    "tm_player_id": player_id,
                    "valuation_date": valuation_date,
                    "market_value_eur": self._parse_market_value_eur(
                        item["new_market_value_raw"]
                    ),
                    "source_url": self.config.base_url,
                    "scraped_at": scrape_date,
                }
            )

        if market_rows:
            upsert_rows(
                self._table("player_market_values"),
                market_rows,
                conflict_columns=["tm_player_id", "valuation_date"],
            )

        return {
            "clubs": len(clubs),
            "players": len(players),
            "player_market_values": len(market_rows),
        }

    def scrape(self) -> dict[str, int]:
        ensure_transfermarkt_tables()

        page = 1
        max_pages = self.config.max_pages_int()
        current_url = self.config.base_url
        previous_response_url = self.config.referer_url
        total_rows = 0
        total_inserted_clubs = 0
        total_inserted_players = 0
        total_inserted_market_values = 0

        while True:
            if max_pages is not None and page > max_pages:
                break

            if page == 1:
                response = self._request_first_page(page)
                current_url = response.url
            else:
                response = self._request_with_retries(
                    current_url,
                    page,
                    referer_url=previous_response_url,
                )
            parsed_rows, next_url = self._parse_page(response.text, page)
            total_rows += len(parsed_rows)
            self.logger.info("Page %s parsed: %s rows", page, len(parsed_rows))
            previous_response_url = response.url

            if not parsed_rows:
                break

            if self.config.dry_run:
                self.logger.info("Dry run enabled; skipping database upserts.")
            else:
                chunk_size = max(1, self.config.batch_size)
                for i in range(0, len(parsed_rows), chunk_size):
                    chunk = parsed_rows[i : i + chunk_size]
                    result = self._persist_rows(chunk)
                    total_inserted_clubs += result["clubs"]
                    total_inserted_players += result["players"]
                    total_inserted_market_values += result["player_market_values"]

            page += 1
            if not next_url:
                break
            current_url = next_url

        return {
            "pages_processed": page - 1,
            "rows_parsed": total_rows,
            "clubs_upserted": total_inserted_clubs,
            "players_upserted": total_inserted_players,
            "player_market_values_upserted": total_inserted_market_values,
            "http_429_count": self._count_429,
            "selected_start_url": self._selected_start_url or self.config.base_url,
        }


def make_transfermarkt_full_url(path: str) -> str:
    """Helper for converting relative links into full Transfermarkt URLs."""
    return urljoin("https://www.transfermarkt.com", path)
