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
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from football_analytics.utils.database import get_postgres_conn, upsert_rows
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
        default_factory=lambda: os.getenv(
            "TRANSFERMARKT_ACCEPT_LANGUAGE", "en-US,en;q=0.9"
        )
    )
    referer_url: str = field(
        default_factory=lambda: os.getenv(
            "TRANSFERMARKT_REFERER", "https://www.transfermarkt.com/"
        )
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
        default_factory=lambda: int(
            os.getenv("TRANSFERMARKT_429_CIRCUIT_BREAKER", "20")
        )
    )
    dry_run: bool = field(
        default_factory=lambda: _env_bool("TRANSFERMARKT_DRY_RUN", False)
    )
    db_schema: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_DB_SCHEMA", "transfermarkt")
    )
    fallback_start_urls: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_FALLBACK_START_URLS", "")
    )
    enrich_profiles: bool = field(
        default_factory=lambda: _env_bool("TRANSFERMARKT_ENRICH_PROFILES", True)
    )
    profile_enrich_limit: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_PROFILE_ENRICH_LIMIT", "all")
    )
    min_marktwert: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_MIN_MARKTWERT", "0")
    )
    latest_transfers_url: str = field(
        default_factory=lambda: os.getenv(
            "TRANSFERMARKT_LATEST_TRANSFERS_URL",
            "https://www.transfermarkt.com/statistik/neuestetransfers",
        )
    )
    latest_transfers_max_pages: str = field(
        default_factory=lambda: os.getenv("TRANSFERMARKT_TRANSFERS_MAX_PAGES", "all")
    )
    latest_transfers_split_by_citizenship: bool = field(
        default_factory=lambda: _env_bool(
            "TRANSFERMARKT_TRANSFERS_SPLIT_BY_CITIZENSHIP", False
        )
    )

    def max_pages_int(self) -> int | None:
        value = self.max_pages.strip().lower()
        if value == "all":
            return None
        return max(int(value), 1)

    def profile_enrich_limit_int(self) -> int | None:
        value = self.profile_enrich_limit.strip().lower()
        if value == "all":
            return None
        return max(int(value), 0)

    def latest_transfers_max_pages_int(self) -> int | None:
        value = self.latest_transfers_max_pages.strip().lower()
        if value == "all":
            return None
        return max(int(value), 1)

    def min_marktwert_query_value(self) -> str:
        raw = (self.min_marktwert or "").strip()
        if not raw:
            return "0"
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return "0"
        return f"{int(digits):,}".replace(",", ".")


class TransfermarktScraper:
    """Scrape Transfermarkt market value changes with ethical request pacing."""

    def __init__(
        self,
        config: TransfermarktConfig | None = None,
        logger: logging.Logger | None = None,
    ):
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
        candidates = [self._with_min_marktwert(self.config.base_url)]

        if not self.config.base_url.endswith("/"):
            candidates.append(self._with_min_marktwert(f"{self.config.base_url}/"))

        # The filtered URL variant often avoids unstable responses on the default landing page.
        candidates.append(
            "https://www.transfermarkt.com/spieler-statistik/marktwertaenderungen/"
            "marktwertetop/?plus=1&galerie=0&position=alle&spielerposition_id=0&"
            "spieler_land_id=0&verein_land_id=&wettbewerb_id=alle&alter=16+-+45&"
            f"filtern_nach_alter=16%3B45&minAlter=16&maxAlter=45&minMarktwert={self.config.min_marktwert_query_value()}&"
            "maxMarktwert=200.000.000&yt0=Show"
        )

        if self.config.fallback_start_urls.strip():
            env_urls = [
                self._with_min_marktwert(u.strip())
                for u in self.config.fallback_start_urls.split(",")
                if u.strip()
            ]
            candidates.extend(env_urls)

        unique: list[str] = []
        for url in candidates:
            if url not in unique:
                unique.append(url)
        return unique

    @staticmethod
    def _with_query_params(url: str, updates: dict[str, str]) -> str:
        parsed = urlparse(url)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        query: dict[str, list[str]] = {}
        for key, value in pairs:
            query.setdefault(key, []).append(value)
        for key, value in updates.items():
            query[key] = [value]
        new_query = urlencode(query, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def _with_min_marktwert(self, url: str) -> str:
        return self._with_query_params(
            url,
            {"minMarktwert": self.config.min_marktwert_query_value()},
        )

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("transfermarkt_scraper")
        if logger.handlers:
            return logger

        logger.setLevel(logging.INFO)
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = (
            log_dir / f"transfermarkt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

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
                    self._reset_session(
                        referer_url=referer_url or self.config.referer_url
                    )

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
            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.HTTPError,
            ) as exc:
                last_error = exc
                backoff = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                status_code = getattr(
                    getattr(exc, "response", None), "status_code", None
                )
                if isinstance(exc, requests.Timeout) or (
                    status_code is not None and status_code >= 500
                ):
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

        raise RuntimeError(
            f"Failed to fetch page {page_num} after retries"
        ) from last_error

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

        raise RuntimeError(
            "Failed to fetch first page from all start URL candidates"
        ) from last_error

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
        for fmt in ("%b %d, %Y", "%b %d, %y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        return text or None

    @staticmethod
    def _parse_height_cm(value: str | None) -> int | None:
        text = (value or "").replace("m", "").replace("€", "").strip()
        match = re.search(r"(\d)[,.](\d{2})", text)
        if match:
            return int(match.group(1)) * 100 + int(match.group(2))
        return None

    @staticmethod
    def _extract_info_pairs(soup: BeautifulSoup) -> dict[str, str]:
        values = []
        for node in soup.select(".info-table .info-table__content"):
            text = TransfermarktScraper._normalize_text(node.get_text(" ", strip=True))
            if text:
                values.append(text)

        pairs: dict[str, str] = {}
        for index in range(0, len(values) - 1, 2):
            label = values[index].rstrip(":")
            value = values[index + 1]
            pairs[label] = value
        return pairs

    @staticmethod
    def _extract_change_direction(cell) -> str | None:
        icon = cell.select_one("span") if cell else None
        classes = icon.get("class", []) if icon else []
        class_blob = " ".join(classes)
        if "green-arrow" in class_blob:
            return "up"
        if "red-arrow" in class_blob:
            return "down"
        if "grey" in class_blob or "gray" in class_blob:
            return "unchanged"
        return None

    @staticmethod
    def _parse_market_value_eur(value: str | None) -> int | None:
        if not value:
            return None
        text = value.strip().replace("€", "").replace(",", ".").lower()
        if "free" in text:
            return 0
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

    @staticmethod
    def _parse_transfer_date(value: str | None) -> date | None:
        text = (value or "").strip()
        for fmt in (
            "%b %d, %Y",
            "%b %d, %y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%d %b %Y",
            "%d %b, %Y",
            "%d.%m.%Y",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _build_transfer_uid(*parts: Any) -> str:
        text = "|".join(str(part or "") for part in parts)
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_next_url(soup: BeautifulSoup, page: int) -> str | None:
        next_link = soup.select_one(
            "a.tm-pagination__link--icon-next"
        ) or soup.select_one("a[rel='next']")
        if next_link and next_link.get("href"):
            return make_transfermarkt_full_url(next_link.get("href"))

        page_links: list[tuple[int, str]] = []
        for anchor in soup.select(
            ".tm-pagination a, div.tm-pagination a, ul.tm-pagination a"
        ):
            href = anchor.get("href")
            page_num = TransfermarktScraper._extract_page_number(href)
            if href and page_num is not None and page_num > page:
                page_links.append((page_num, href))

        if not page_links:
            return None

        next_href = min(page_links, key=lambda x: x[0])[1]
        return make_transfermarkt_full_url(next_href)

    def _parse_page(
        self, html: str, page: int
    ) -> tuple[list[dict[str, Any]], str | None]:
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
            player_image = cells[0].select_one("img")
            player_tm_id = self._extract_tm_id(player_href) or self._fallback_tm_id(
                "player", player_name
            )

            position = None
            if player_inline:
                trs = player_inline.select("tr")
                if len(trs) > 1:
                    position = trs[1].get_text(" ", strip=True)

            nationality = (
                ", ".join(
                    img.get("title")
                    for img in cells[1].select("img")
                    if img.get("title")
                )
                or None
            )
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
            club_img = cells[3].select_one("img")
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
                    percentage_value = (
                        float(percentage_clean) if percentage_clean else None
                    )
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
                    "player_image_url": (
                        player_image.get("src") if player_image else None
                    ),
                    "player_profile_url": (
                        make_transfermarkt_full_url(player_href)
                        if player_href
                        else None
                    ),
                    "club_badge_url": club_img.get("src") if club_img else None,
                    "club_profile_url": (
                        make_transfermarkt_full_url(club_href) if club_href else None
                    ),
                    "new_market_value_raw": new_mv_raw,
                    "old_market_value_raw": old_mv_raw,
                    "difference_raw": diff_raw,
                    "change_direction": self._extract_change_direction(cells[4]),
                    "percentage_change": percentage_value,
                    "changed_on": self._parse_changed_on(changed_on_raw),
                }
            )

        next_url = self._extract_next_url(soup, page)
        return rows, next_url

    def _parse_latest_transfers_page(
        self,
        html: str,
        page: int,
        source_url: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        soup = BeautifulSoup(html, "lxml")
        table = (
            soup.select_one("table.items")
            or soup.select_one(".box table.items")
            or soup.select_one("table[class*='items']")
            or soup.select_one(".items")
        )
        if table is None:
            self.logger.warning("No latest transfers table found on page %s", page)
            title = soup.title.get_text(strip=True) if soup.title else "n/a"
            self.logger.warning(
                "Unexpected HTML title on latest transfers page %s: %s", page, title
            )
            return [], None

        headers = [
            self._normalize_text(th.get_text(" ", strip=True) or "") or ""
            for th in table.select("thead th")
        ]
        header_lookup = [header.lower() for header in headers]

        def _find_col(keywords: tuple[str, ...], default_idx: int) -> int:
            for idx, header in enumerate(header_lookup):
                if any(keyword in header for keyword in keywords):
                    return idx
            return default_idx

        idx_player = _find_col(("player",), 0)
        idx_age = _find_col(("age",), 1)
        idx_nationality = _find_col(("nat", "citizenship"), 2)
        idx_from = _find_col(("left", "from", "old club"), 3)
        idx_to = _find_col(("joined", "to", "new club"), 4)
        idx_fee = _find_col(("fee", "abl", "cost", "co\u00fbt", "tarif"), -1)
        idx_date = _find_col(("date", "day", "datum", "fecha", "data"), -1)
        idx_market_value = _find_col(
            ("market value", "mv", "marktwert", "valor", "valeur"), -1
        )

        rows: list[dict[str, Any]] = []
        for row in table.select("tr.odd, tr.even"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 6:
                continue

            # Fallbacks based on known table layouts:
            # compact:  [player, age, nat, left, joined, fee]
            # detailed: [player, age, nat, left, joined, date, market value, fee]
            effective_idx_fee = idx_fee
            effective_idx_date = idx_date
            effective_idx_market_value = idx_market_value
            if len(cells) >= 8:
                if effective_idx_date < 0:
                    effective_idx_date = 5
                if effective_idx_market_value < 0:
                    effective_idx_market_value = 6
                if effective_idx_fee < 0:
                    effective_idx_fee = 7
            else:
                if effective_idx_fee < 0:
                    effective_idx_fee = 5

            def _cell(index: int):
                if index < 0 or index >= len(cells):
                    return None
                return cells[index]

            player_cell = _cell(idx_player)
            player_inline = (
                player_cell.select_one("table.inline-table") if player_cell else None
            )
            player_anchor = (
                player_inline.select_one("td.hauptlink a") if player_inline else None
            )
            if player_anchor is None and player_cell:
                player_anchor = player_cell.select_one("a")
            player_name = player_anchor.get_text(strip=True) if player_anchor else None
            player_href = player_anchor.get("href") if player_anchor else None
            player_image = player_cell.select_one("img") if player_cell else None
            player_tm_id = self._extract_tm_id(player_href)

            position = None
            if player_inline:
                trs = player_inline.select("tr")
                if len(trs) > 1:
                    position = trs[1].get_text(" ", strip=True)

            nationality_cell = _cell(idx_nationality)
            nationality = (
                ", ".join(
                    img.get("title")
                    for img in nationality_cell.select("img")
                    if img.get("title")
                )
                if nationality_cell
                else None
            )
            if not nationality and nationality_cell:
                nationality = self._normalize_text(
                    nationality_cell.get_text(" ", strip=True)
                )

            age_cell = _cell(idx_age)
            age = (
                self._parse_age(age_cell.get_text(" ", strip=True))
                if age_cell
                else None
            )

            from_cell = _cell(idx_from)
            from_anchor = from_cell.select_one("a") if from_cell else None
            from_club_name = None
            from_club_href = None
            if from_anchor:
                from_club_name = from_anchor.get("title") or from_anchor.get_text(
                    strip=True
                )
                from_club_href = from_anchor.get("href")
            if not from_club_name and from_cell:
                from_img = from_cell.select_one("img")
                if from_img:
                    from_club_name = from_img.get("title")

            to_cell = _cell(idx_to)
            to_anchor = to_cell.select_one("a") if to_cell else None
            to_club_name = None
            to_club_href = None
            if to_anchor:
                to_club_name = to_anchor.get("title") or to_anchor.get_text(strip=True)
                to_club_href = to_anchor.get("href")
            if not to_club_name and to_cell:
                to_img = to_cell.select_one("img")
                if to_img:
                    to_club_name = to_img.get("title")

            fee_cell = _cell(effective_idx_fee)
            transfer_fee_raw = (
                self._normalize_text(fee_cell.get_text(" ", strip=True))
                if fee_cell
                else None
            )
            date_cell = _cell(effective_idx_date)
            transfer_date_raw = (
                self._normalize_text(date_cell.get_text(" ", strip=True))
                if date_cell
                else None
            )

            mv_cell = _cell(effective_idx_market_value)
            market_value_raw = (
                self._normalize_text(mv_cell.get_text(" ", strip=True))
                if mv_cell
                else None
            )

            row_uid = self._build_transfer_uid(
                player_tm_id,
                player_name,
                from_club_name,
                to_club_name,
                transfer_fee_raw,
                transfer_date_raw,
            )

            rows.append(
                {
                    "transfer_uid": row_uid,
                    "tm_player_id": self._to_int(player_tm_id),
                    "player_name": player_name or "Unknown Player",
                    "player_profile_url": (
                        make_transfermarkt_full_url(player_href)
                        if player_href
                        else None
                    ),
                    "player_image_url": (
                        player_image.get("src") if player_image else None
                    ),
                    "age": age,
                    "position": position,
                    "nationality": nationality,
                    "from_tm_club_id": self._to_int(
                        self._extract_tm_id(from_club_href)
                    ),
                    "from_club_name": from_club_name,
                    "from_club_profile_url": (
                        make_transfermarkt_full_url(from_club_href)
                        if from_club_href
                        else None
                    ),
                    "to_tm_club_id": self._to_int(self._extract_tm_id(to_club_href)),
                    "to_club_name": to_club_name,
                    "to_club_profile_url": (
                        make_transfermarkt_full_url(to_club_href)
                        if to_club_href
                        else None
                    ),
                    "market_value_eur": self._parse_market_value_eur(market_value_raw),
                    "market_value_raw": market_value_raw,
                    "transfer_fee_eur": self._parse_market_value_eur(transfer_fee_raw),
                    "transfer_fee_raw": transfer_fee_raw,
                    "transfer_date": self._parse_transfer_date(transfer_date_raw),
                    "source_url": source_url,
                }
            )

        return rows, self._extract_next_url(soup, page)

    def _table(self, table_name: str) -> str:
        return f"{self.config.db_schema}.{table_name}"

    def _select_ids_missing_profile(
        self,
        table_name: str,
        id_column: str,
        ids: list[int],
    ) -> set[int]:
        if not ids:
            return set()

        conn = get_postgres_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    (
                        f"SELECT {id_column} FROM {self._table(table_name)} "
                        f"WHERE {id_column} = ANY(%s) AND profile_last_scraped_at IS NULL"
                    ),
                    (ids,),
                )
                return {int(row[0]) for row in cur.fetchall()}
        finally:
            conn.close()

    def _enrich_player_profiles(self, players_to_enrich: list[dict[str, Any]]) -> int:
        if not players_to_enrich:
            return 0

        updates: list[dict[str, Any]] = []
        for player in players_to_enrich:
            profile_url = player.get("player_profile_url")
            player_id = self._to_int(player.get("player_tm_id"))
            if player_id is None or not profile_url:
                continue

            response = self._request_with_retries(
                profile_url,
                1,
                referer_url=self.config.base_url,
            )
            soup = BeautifulSoup(response.text, "lxml")
            pairs = self._extract_info_pairs(soup)

            citizenship = pairs.get("Citizenship") or pairs.get("Citizenship:")
            updates.append(
                {
                    "tm_player_id": player_id,
                    "full_name": player.get("player_name") or "Unknown Player",
                    "home_name": pairs.get("Name in home country"),
                    "date_of_birth": self._parse_changed_on(
                        (pairs.get("Date of birth/Age") or "").split("(")[0].strip()
                    ),
                    "place_of_birth": pairs.get("Place of birth"),
                    "height_cm": self._parse_height_cm(pairs.get("Height")),
                    "nationality": player.get("nationality") or citizenship,
                    "citizenship_raw": citizenship,
                    "preferred_foot": pairs.get("Foot"),
                    "main_position": player.get("position"),
                    "detailed_position": pairs.get("Position"),
                    "current_tm_club_id": (
                        str(player.get("club_tm_id"))
                        if player.get("club_tm_id")
                        else None
                    ),
                    "joined_current_club_on": self._parse_changed_on(
                        pairs.get("Joined")
                    ),
                    "contract_expires_on": self._parse_changed_on(
                        pairs.get("Contract expires")
                    ),
                    "last_contract_extension_on": self._parse_changed_on(
                        pairs.get("Last contract extension")
                    ),
                    "player_image_url": player.get("player_image_url"),
                    "profile_url": profile_url,
                    "profile_last_scraped_at": datetime.utcnow().replace(microsecond=0),
                    "scraped_at": datetime.utcnow().replace(microsecond=0),
                    "updated_at": datetime.utcnow().replace(microsecond=0),
                }
            )

        if updates:
            upsert_rows(
                self._table("players"), updates, conflict_columns="tm_player_id"
            )
        return len(updates)

    def _enrich_club_profiles(self, clubs_to_enrich: list[dict[str, Any]]) -> int:
        if not clubs_to_enrich:
            return 0

        updates: list[dict[str, Any]] = []
        for club in clubs_to_enrich:
            profile_url = club.get("club_profile_url")
            club_id = self._to_int(club.get("club_tm_id"))
            if club_id is None or not profile_url:
                continue

            response = self._request_with_retries(
                profile_url,
                1,
                referer_url=self.config.base_url,
            )
            soup = BeautifulSoup(response.text, "lxml")

            official_name = self._normalize_text(
                (
                    soup.select_one("[itemprop='legalName']")
                    or soup.select_one(".info-table .info-table__content--bold")
                ).get_text(" ", strip=True)
                if (
                    soup.select_one("[itemprop='legalName']")
                    or soup.select_one(".info-table .info-table__content--bold")
                )
                else None
            )
            founded_on = self._parse_changed_on(
                self._normalize_text(
                    soup.select_one("[itemprop='foundingDate']").get_text(
                        " ", strip=True
                    )
                    if soup.select_one("[itemprop='foundingDate']")
                    else None
                )
            )
            address_values = [
                self._normalize_text(node.get_text(" ", strip=True))
                for node in soup.select(
                    "[itemprop='address'] .info-table__content--bold"
                )
            ]
            address_values = [value for value in address_values if value]
            crest = soup.select_one(".dataBild img") or soup.select_one(
                ".data-header__profile-container img"
            )

            updates.append(
                {
                    "tm_club_id": club_id,
                    "club_name": club.get("club_name") or "Unknown Club",
                    "country": (
                        address_values[-1] if address_values else club.get("country")
                    ),
                    "official_name": official_name,
                    "founded_on": founded_on,
                    "address_raw": (
                        " | ".join(address_values) if address_values else None
                    ),
                    "city": address_values[0] if address_values else None,
                    "crest_url": club.get("club_badge_url")
                    or (crest.get("src") if crest else None),
                    "profile_url": profile_url,
                    "profile_last_scraped_at": datetime.utcnow().replace(microsecond=0),
                    "scraped_at": datetime.utcnow().replace(microsecond=0),
                }
            )

        if updates:
            upsert_rows(self._table("clubs"), updates, conflict_columns="tm_club_id")
        return len(updates)

    def _enrich_profiles_for_rows(
        self, parsed_rows: list[dict[str, Any]]
    ) -> dict[str, int]:
        if not self.config.enrich_profiles:
            return {"player_profiles": 0, "club_profiles": 0}

        limit = self.config.profile_enrich_limit_int()

        unique_players: dict[int, dict[str, Any]] = {}
        unique_clubs: dict[int, dict[str, Any]] = {}
        for item in parsed_rows:
            player_id = self._to_int(item.get("player_tm_id"))
            club_id = self._to_int(item.get("club_tm_id"))
            if player_id is not None and player_id not in unique_players:
                unique_players[player_id] = item
            if club_id is not None and club_id not in unique_clubs:
                unique_clubs[club_id] = item

        player_ids = list(unique_players.keys())
        club_ids = list(unique_clubs.keys())
        missing_player_ids = self._select_ids_missing_profile(
            "players", "tm_player_id", player_ids
        )
        missing_club_ids = self._select_ids_missing_profile(
            "clubs", "tm_club_id", club_ids
        )

        players_to_enrich = [
            unique_players[player_id]
            for player_id in player_ids
            if player_id in missing_player_ids
        ]
        clubs_to_enrich = [
            unique_clubs[club_id] for club_id in club_ids if club_id in missing_club_ids
        ]

        if limit is not None:
            players_to_enrich = players_to_enrich[:limit]
            clubs_to_enrich = clubs_to_enrich[:limit]

        return {
            "player_profiles": self._enrich_player_profiles(players_to_enrich),
            "club_profiles": self._enrich_club_profiles(clubs_to_enrich),
        }

    def _persist_rows(self, parsed_rows: list[dict[str, Any]]) -> dict[str, int]:
        if not parsed_rows:
            return {
                "clubs": 0,
                "players": 0,
                "player_market_values": 0,
                "player_profiles": 0,
                "club_profiles": 0,
            }

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
                "crest_url": item.get("club_badge_url"),
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
                "player_image_url": item.get("player_image_url"),
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
                    "market_value_raw": item["new_market_value_raw"],
                    "change_direction": item.get("change_direction"),
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

        enrichment_counts = self._enrich_profiles_for_rows(parsed_rows)

        return {
            "clubs": len(clubs),
            "players": len(players),
            "player_market_values": len(market_rows),
            "player_profiles": enrichment_counts["player_profiles"],
            "club_profiles": enrichment_counts["club_profiles"],
        }

    def _persist_latest_transfers(self, transfer_rows: list[dict[str, Any]]) -> int:
        if not transfer_rows:
            return 0

        upsert_rows(
            self._table("latest_transfers"),
            transfer_rows,
            conflict_columns="transfer_uid",
        )
        return len(transfer_rows)

    def _fetch_citizenship_ids(self) -> list[tuple[int, str]]:
        """Fetch the citizenship <select> from the latest transfers page and return (id, name) pairs."""
        response = self._request_with_retries(
            self._with_query_params(
                self._with_min_marktwert(self.config.latest_transfers_url),
                {"plus": "1"},
            ),
            1,
            referer_url=self.config.referer_url,
        )
        soup = BeautifulSoup(response.text, "lxml")

        # The citizenship filter select has name="land_id" (distinct from verein_land_id)
        # Prefer the second occurrence - first is "Clubs from", second is "Citizenship"
        selects = soup.find_all("select", {"name": "land_id"})
        citizenship_select = (
            selects[1] if len(selects) >= 2 else (selects[0] if selects else None)
        )

        if citizenship_select is None:
            self.logger.warning(
                "Could not locate citizenship select on latest transfers page."
            )
            return []

        result: list[tuple[int, str]] = []
        for option in citizenship_select.find_all("option"):
            raw_value = option.get("value", "").strip()
            if not raw_value or raw_value == "0":
                continue
            try:
                country_name = option.get_text(strip=True)
                result.append((int(raw_value), country_name))
                self.logger.info(
                    "Citizenship option extracted: %s (land_id=%s)",
                    country_name,
                    raw_value,
                )
            except ValueError:
                continue

        self.logger.info(
            "Found %s citizenship options on latest transfers page.", len(result)
        )
        return result

    def _scrape_latest_transfers_from_url(self, start_url: str) -> tuple[int, int, int]:
        """Scrape one paginated latest-transfers URL. Returns (pages, rows_parsed, upserted)."""
        page = 1
        max_pages = self.config.latest_transfers_max_pages_int()
        current_url = start_url
        previous_response_url = self.config.referer_url
        total_rows = 0
        total_upserted = 0

        while True:
            if max_pages is not None and page > max_pages:
                break

            response = self._request_with_retries(
                current_url,
                page,
                referer_url=previous_response_url,
            )
            parsed_rows, next_url = self._parse_latest_transfers_page(
                response.text,
                page,
                source_url=response.url,
            )
            total_rows += len(parsed_rows)
            self.logger.info(
                "Latest transfers [%s] page %s parsed: %s rows",
                start_url,
                page,
                len(parsed_rows),
            )
            previous_response_url = response.url

            if not parsed_rows:
                break

            if self.config.dry_run:
                self.logger.info("Dry run enabled; skipping latest transfers upserts.")
            else:
                chunk_size = max(1, self.config.batch_size)
                for i in range(0, len(parsed_rows), chunk_size):
                    chunk = parsed_rows[i : i + chunk_size]
                    total_upserted += self._persist_latest_transfers(chunk)

            page += 1
            if not next_url:
                break
            current_url = next_url

        return page - 1, total_rows, total_upserted

    def _scrape_latest_transfers(self) -> dict[str, int]:
        base_url = self._with_query_params(
            self._with_min_marktwert(self.config.latest_transfers_url),
            {"plus": "1"},
        )
        urls = [base_url]

        self.logger.info(
            "Latest transfers citizenship split selected: %s",
            self.config.latest_transfers_split_by_citizenship,
        )

        if self.config.latest_transfers_split_by_citizenship:
            # Split by citizenship: for each country fetch its own paginated result set.
            # Each country gets the full 10-page cap (~25 rows/page) independently,
            # so no country's transfers are truncated by the global listing limit.
            citizenship_ids = self._fetch_citizenship_ids()
            if not citizenship_ids:
                self.logger.warning(
                    "No citizenship IDs found; falling back to base URLs."
                )
            else:
                urls = []
                for country_id, country_name in citizenship_ids:
                    urls.append(
                        (
                            self._with_query_params(
                                base_url,
                                {"land_id": str(country_id)},
                            ),
                            country_name,
                        )
                    )

                total_pages = 0
                total_rows = 0
                total_upserted = 0
                for url, country_name in urls:
                    self.logger.info(
                        "Citizenship selected; extracting nationality: %s", country_name
                    )
                    pages, rows, upserted = self._scrape_latest_transfers_from_url(url)
                    total_pages += pages
                    total_rows += rows
                    total_upserted += upserted

                return {
                    "latest_transfers_pages_processed": total_pages,
                    "latest_transfers_rows_parsed": total_rows,
                    "latest_transfers_upserted": total_upserted,
                }

        total_pages = 0
        total_rows = 0
        total_upserted = 0

        for url in urls:
            pages, rows, upserted = self._scrape_latest_transfers_from_url(url)
            total_pages += pages
            total_rows += rows
            total_upserted += upserted

        return {
            "latest_transfers_pages_processed": total_pages,
            "latest_transfers_rows_parsed": total_rows,
            "latest_transfers_upserted": total_upserted,
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
        total_enriched_player_profiles = 0
        total_enriched_club_profiles = 0

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
                    total_enriched_player_profiles += result["player_profiles"]
                    total_enriched_club_profiles += result["club_profiles"]

            page += 1
            if not next_url:
                break
            current_url = next_url

        latest_transfers_summary = self._scrape_latest_transfers()

        return {
            "pages_processed": page - 1,
            "rows_parsed": total_rows,
            "clubs_upserted": total_inserted_clubs,
            "players_upserted": total_inserted_players,
            "player_market_values_upserted": total_inserted_market_values,
            "player_profiles_enriched": total_enriched_player_profiles,
            "club_profiles_enriched": total_enriched_club_profiles,
            "http_429_count": self._count_429,
            "selected_start_url": self._selected_start_url or self.config.base_url,
            **latest_transfers_summary,
        }


def make_transfermarkt_full_url(path: str) -> str:
    """Helper for converting relative links into full Transfermarkt URLs."""
    return urljoin("https://www.transfermarkt.com", path)
