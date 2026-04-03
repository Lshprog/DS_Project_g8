#!/usr/bin/env python3
"""
Business Times (Energy & Commodities) scraper — sitemap-based.

Instead of Playwright scroll, this script:
1. Generates monthly sitemap URLs for the lookback window.
2. Fetches each sitemap with requests (no browser needed).
3. Filters URLs by energy/commodities keywords in the slug — not just the
   /companies-markets/energy-commodities/ path — so articles filed under
   /international/, /opinion-features/, /singapore/ etc. are also captured.
4. Uses <lastmod> from the sitemap as published_at (no per-article fetches).
5. Optionally fetches article HTML to get title + summary.
6. Saves to the same JSONL format as the Playwright version.

Encoding fix (v2):
- Force UTF-8 decoding on all responses via resp.encoding = "utf-8".
- _clean_text() re-encodes through UTF-8 to strip mojibake remnants.

Keyword filter fix (v3):
- Replaced strict path filter (/companies-markets/energy-commodities/) with
  a broad keyword regex matched against the URL slug, capturing articles filed
  under /international/, /opinion-features/, /singapore/, etc.
"""

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

# ── constants ────────────────────────────────────────────────────────────────

BASE = "https://www.businesstimes.com.sg"
SITEMAP_PATTERN = "https://www.businesstimes.com.sg/sitemap/{year}/{month:02d}/feeds.xml"
DEFAULT_LOOKBACK_DAYS = 365 * 2

REQUEST_TIMEOUT = 30           # seconds per HTTP request
RETRY_COUNT = 3                # retries per failed request
RETRY_BACKOFF = 2.0            # seconds between retries
FETCH_ARTICLE_DETAILS = False  # set True to fetch title/summary from article HTML
ARTICLE_DELAY = 0.5            # seconds between article fetches if enabled

# Keyword regex matched against the URL slug/path.
# Catches energy & commodities articles regardless of which section they are
# filed under (/international/, /opinion-features/, /singapore/, etc.).
ENERGY_KEYWORDS = re.compile(
    r"oil|gas|lng|crude|petrol|fuel|energy|gold|silver|coal|"
    r"commodit|copper|nickel|alumin|lithium|uranium|opec|aramco|"
    r"petronas|pertamina|sinopec|refin|barrel|hormuz|brent|wti|"
    r"naphtha|kerosene|diesel|palm.oil|natural.gas|shale|offshore|"
    r"rig|pipeline|tanker|refinery|downstream|upstream|midstream",
    re.IGNORECASE,
)

SGT = timezone(timedelta(hours=8))
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ── data model ───────────────────────────────────────────────────────────────

@dataclass
class Item:
    title: str
    summary: str
    url: str
    published_at: Optional[str]   # UTC ISO8601
    section: str


# ── helpers ──────────────────────────────────────────────────────────────────

def _clean_text(s: str) -> str:
    # Re-encode through UTF-8 to drop mojibake remnants, then normalise whitespace
    s = (s or "").encode("utf-8", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", s).strip()


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SGT)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _slug_to_title(url: str) -> str:
    """Best-effort title from URL slug when article fetch is disabled."""
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return _clean_text(slug.replace("-", " ").title())


def _get(url: str, retries: int = RETRY_COUNT, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            # Always force UTF-8 — don't trust the server's Content-Type charset,
            # which is often wrong and causes smart quotes to appear as â / Â garbage.
            resp.encoding = "utf-8"
            if resp.status_code < 400:
                return resp
            print(f"  HTTP {resp.status_code} for {url}")
        except Exception as e:
            print(f"  Request error ({attempt}/{retries}): {e}")
        if attempt < retries:
            time.sleep(RETRY_BACKOFF * attempt)
    return None


def _fetch_article_details(url: str) -> tuple[str, str]:
    """Fetch title and first paragraph from article HTML."""
    resp = _get(url)
    if not resp:
        return _slug_to_title(url), ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title — prefer og:title meta, fall back to h1
    title = ""
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        title = _clean_text(og["content"])
    if not title:
        tag = soup.find("h1")
        if tag:
            title = _clean_text(tag.get_text(" "))
    if not title:
        title = _slug_to_title(url)

    # Summary — first substantial paragraph in article body
    summary = ""
    for p in soup.select("article p, [data-testid='article-body'] p"):
        txt = _clean_text(p.get_text(" "))
        if txt and len(txt) > 40:
            summary = txt
            break

    return title, summary


def _monthly_sitemap_urls(lookback_days: int) -> List[str]:
    """Generate sitemap URLs for every month in the lookback window."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    urls = []
    cur = now.replace(day=1)
    while cur >= cutoff.replace(day=1):
        urls.append(SITEMAP_PATTERN.format(year=cur.year, month=cur.month))
        if cur.month == 1:
            cur = cur.replace(year=cur.year - 1, month=12)
        else:
            cur = cur.replace(month=cur.month - 1)
    return urls


def _is_energy_url(url: str) -> bool:
    """Return True if the URL slug contains an energy/commodities keyword."""
    path = urlparse(url).path
    return bool(ENERGY_KEYWORDS.search(path))


def _parse_sitemap(xml_text: str, cutoff: datetime) -> List[tuple[str, str]]:
    """
    Parse a monthly sitemap XML and return (url, lastmod) pairs for
    energy/commodities articles within the cutoff window.
    Matches on URL slug keywords rather than a strict section path.
    """
    results = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return results

    for url_el in root.findall("sm:url", NS):
        loc = url_el.findtext("sm:loc", "", NS).strip()
        lastmod = url_el.findtext("sm:lastmod", "", NS).strip()

        if not _is_energy_url(loc):
            continue

        dt = _parse_iso_datetime(lastmod)
        if dt and dt < cutoff:
            continue

        results.append((_normalize_url(loc), lastmod))

    return results


# ── main scrape ──────────────────────────────────────────────────────────────

def scrape(
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    fetch_article_details: bool = FETCH_ARTICLE_DETAILS,
    article_delay: float = ARTICLE_DELAY,
    existing_by_url: Optional[Dict[str, Item]] = None,
) -> List[Item]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    existing_by_url = existing_by_url or {}
    seen: Dict[str, str] = {}   # url -> lastmod

    sitemap_urls = _monthly_sitemap_urls(lookback_days)
    print(f"Fetching {len(sitemap_urls)} monthly sitemaps "
          f"(cutoff: {cutoff.date().isoformat()})...")

    for sm_url in sitemap_urls:
        print(f"  {sm_url}", end=" ... ", flush=True)
        resp = _get(sm_url)
        if not resp:
            print("FAILED")
            continue
        pairs = _parse_sitemap(resp.text, cutoff)
        before = len(seen)
        for url, lastmod in pairs:
            if url not in seen:
                seen[url] = lastmod
        print(f"{len(pairs)} energy articles (+{len(seen) - before} new)")

    print(f"\nTotal unique energy-commodities URLs: {len(seen)}")

    # ── build Item list ───────────────────────────────────────────────────────
    items: List[Item] = []
    for idx, (url, lastmod) in enumerate(seen.items(), start=1):
        published_at = None
        dt = _parse_iso_datetime(lastmod)
        if dt:
            published_at = _to_utc_iso(dt)

        # Try cache first
        cached = existing_by_url.get(url)
        if cached:
            title = cached.title or _slug_to_title(url)
            summary = cached.summary or ""
        elif fetch_article_details:
            title, summary = _fetch_article_details(url)
            if article_delay > 0:
                time.sleep(article_delay)
        else:
            title = _slug_to_title(url)
            summary = ""

        items.append(Item(
            title=title,
            summary=summary,
            url=url,
            published_at=published_at,
            section="Energy & Commodities",
        ))

        if idx % 100 == 0 or idx == len(seen):
            print(f"  Built {idx}/{len(seen)} items")

    # Sort newest first
    items.sort(
        key=lambda it: _parse_iso_datetime(it.published_at) or datetime(1970, 1, 1, tzinfo=timezone.utc),
        reverse=True,
    )
    return items


# ── persistence ───────────────────────────────────────────────────────────────

def _load_existing(path: str) -> Dict[str, Item]:
    out = Path(path)
    if not out.exists():
        return {}
    index: Dict[str, Item] = {}
    with out.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = _normalize_url(raw.get("url", ""))
            if not url:
                continue
            index[url] = Item(
                title=_clean_text(raw.get("title", "")),
                summary=_clean_text(raw.get("summary", "")),
                url=url,
                published_at=raw.get("published_at"),
                section=raw.get("section", "Energy & Commodities"),
            )
    return index


def _save_jsonl(items: List[Item], path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")
    tmp.replace(out)
    print(f"Saved {len(items)} items -> {out}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _project_path(*parts: str) -> str:
    here = Path(__file__).resolve()
    cur = here.parent
    for _ in range(10):
        if (cur / "README.md").exists() or (cur / ".git").exists():
            return str(cur.joinpath(*parts).resolve())
        cur = cur.parent
    return str(here.parent.joinpath(*parts).resolve())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape BT Energy & Commodities via monthly sitemaps into JSONL."
    )
    parser.add_argument(
        "--output",
        default=_project_path("data", "raw", "news", "bt_energy_commodities_2y_sitemap.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS,
        help=f"How many days back to collect. (default: {DEFAULT_LOOKBACK_DAYS})",
    )
    parser.add_argument(
        "--fetch-details", action="store_true", default=False,
        help="Fetch each article page to get proper title and summary (slow but richer).",
    )
    parser.add_argument(
        "--article-delay", type=float, default=ARTICLE_DELAY,
        help=f"Seconds between article fetches when --fetch-details is on. (default: {ARTICLE_DELAY})",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Do not load existing output as cache for titles/summaries.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    existing = {}
    if not args.no_cache:
        existing = _load_existing(args.output)
        print(f"Loaded {len(existing)} cached entries from {args.output}")

    data = scrape(
        lookback_days=args.lookback_days,
        fetch_article_details=args.fetch_details,
        article_delay=args.article_delay,
        existing_by_url=existing,
    )
    _save_jsonl(data, args.output)
    print(f"Done: {len(data)} articles")