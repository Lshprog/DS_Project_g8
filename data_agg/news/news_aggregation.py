#!/usr/bin/env python3
"""
Business Times (Energy & Commodities) scraper using Playwright.

What it does:
- Opens the section page in a real browser context (JS-rendered, infinite scroll).
- Scrolls to load older cards until we have enough unique articles AND we've crossed the 2-year cutoff.
- Extracts title + summary from the listing cards.
- Visits each article URL to extract published_at reliably (meta tag / JSON-LD / visible span).
- Saves to JSONL.

Install:
  pip install playwright python-dateutil bs4 requests
  playwright install chromium

Run:
  python scrape_bt_playwright.py
"""

import json
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


BASE = "https://www.businesstimes.com.sg"
SECTION_URL = "https://www.businesstimes.com.sg/companies-markets/energy-commodities"

# Politeness / stability knobs
SCROLL_PAUSE_SECONDS = 2.5          # wait after each scroll for XHR to populate cards
ARTICLE_DELAY_SECONDS = 1.0         # delay between article visits
MAX_SCROLLS = 200                   # hard cap
MIN_PAGES_WORTH = 10                # "at least 10 pages" approximation (cards/page ~ 10)
APPROX_CARDS_PER_PAGE = 10          # adjust if BT shows more/less
TARGET_MIN_ITEMS = MIN_PAGES_WORTH * APPROX_CARDS_PER_PAGE

# Date handling
SGT = timezone(timedelta(hours=8))


@dataclass
class Item:
    title: str
    summary: str
    url: str
    published_at: Optional[str]  # UTC ISO8601
    section: str


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SGT)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_published_at_from_article_html(html: str) -> Optional[str]:
    """
    Robust publish time extraction from article HTML.
    Priority:
      1) meta[name="article:published_time"] content="...+08:00"
      2) JSON-LD datePublished (often Z)
      3) span[data-testid="article-published-time"] "Published ... · 05:36 PM"
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) Meta tag: article:published_time
    meta = soup.select_one('meta[name="article:published_time"]')
    if meta and meta.get("content"):
        try:
            dt = dateparser.parse(meta["content"])
            return _to_utc_iso(dt)
        except Exception:
            pass

    # 2) JSON-LD: datePublished
    for s in soup.select('script[type="application/ld+json"]'):
        txt = s.string or s.get_text(strip=True)
        if not txt:
            continue
        try:
            data = json.loads(txt)
        except Exception:
            continue

        def _walk(obj):
            if isinstance(obj, dict):
                if obj.get("datePublished"):
                    return obj["datePublished"]
                for v in obj.values():
                    found = _walk(v)
                    if found:
                        return found
            elif isinstance(obj, list):
                for it in obj:
                    found = _walk(it)
                    if found:
                        return found
            return None

        date_pub = _walk(data)
        if date_pub:
            try:
                dt = dateparser.parse(date_pub)
                return _to_utc_iso(dt)
            except Exception:
                pass

    # 3) Visible span
    span = soup.select_one('span[data-testid="article-published-time"]')
    if span:
        txt = _clean_text(span.get_text(" ", strip=True))
        if txt:
            txt = re.sub(r"^\s*Published\s*", "", txt, flags=re.IGNORECASE).strip()
            try:
                dt = dateparser.parse(txt, dayfirst=False)
                return _to_utc_iso(dt)
            except Exception:
                pass

    return None


def _project_path(*parts: str) -> str:
    """
    Resolve path relative to repo root by finding README.md or .git.
    Falls back to script directory.
    """
    here = Path(__file__).resolve()
    cur = here.parent
    for _ in range(10):
        if (cur / "README.md").exists() or (cur / ".git").exists():
            return str((cur.joinpath(*parts)).resolve())
        cur = cur.parent
    return str((here.parent.joinpath(*parts)).resolve())


def _save_jsonl(items: List[Item], path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")


def _extract_cards_from_dom(page) -> Dict[str, Item]:
    """
    Extract card title/summary/url from the SECTION page DOM.
    Returns dict keyed by URL.
    """
    cards: Dict[str, Item] = {}

    # BT uses stable data-testid for card titles.
    # We locate anchors, then look upward for summary text within the card container.
    anchors = page.locator('h3[data-testid="card-title-component"] a')
    count = anchors.count()
    if count == 0:
        # fallback
        anchors = page.locator("h3 a")
        count = anchors.count()

    for i in range(count):
        a = anchors.nth(i)
        href = a.get_attribute("href")
        title = _clean_text(a.inner_text() or "")
        if not href or not title:
            continue

        url = urljoin(BASE, href)

        # Try to find a summary near the card.
        # We'll climb to a reasonable ancestor and look for a paragraph.
        summary = ""
        try:
            # Find the nearest ancestor that likely represents a card
            container = a.locator("xpath=ancestor::*[self::article or self::li or self::div or self::section][1]")
            p = container.locator("p").first
            if p.count():
                summary = _clean_text(p.inner_text() or "")
        except Exception:
            summary = ""

        cards[url] = Item(
            title=title,
            summary=summary,
            url=url,
            published_at=None,
            section="Energy & Commodities",
        )

    return cards


def scrape_bt_energy_commodities_two_years(
    min_items: int = TARGET_MIN_ITEMS,
    max_scrolls: int = MAX_SCROLLS,
    scroll_pause_seconds: float = SCROLL_PAUSE_SECONDS,
    article_delay_seconds: float = ARTICLE_DELAY_SECONDS,
    headless: bool = True,
) -> List[Item]:
    """
    Scroll-load cards until we have at least `min_items` unique URLs.
    Then visit each article to populate published_at and filter to last 2 years.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * 2)
    seen: Dict[str, Item] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
            ),
            locale="en-SG",
            timezone_id="Asia/Singapore",
        )
        page = context.new_page()

        print("Opening:", SECTION_URL)
        page.goto(SECTION_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for initial cards
        try:
            page.wait_for_selector('h3[data-testid="card-title-component"] a', timeout=20000)
        except PlaywrightTimeoutError:
            # fallback selector
            page.wait_for_selector("h3 a", timeout=20000)

        last_count = 0
        stagnant_scrolls = 0

        for s in range(1, max_scrolls + 1):
            cards = _extract_cards_from_dom(page)
            before = len(seen)
            seen.update(cards)
            after = len(seen)

            print(f"Scroll {s}/{max_scrolls}: unique_urls={after} (+{after - before})")

            # Stop if we have enough items and we're not gaining much
            if after >= min_items and (after - before) == 0:
                print(f"Reached min_items={min_items} and no new items on this scroll. Stopping scroll.")
                break

            # Detect stagnation
            if after == last_count:
                stagnant_scrolls += 1
            else:
                stagnant_scrolls = 0
            last_count = after

            if stagnant_scrolls >= 5 and after >= min_items:
                print("Stagnant for 5 scrolls after reaching min_items. Stopping scroll.")
                break
            if stagnant_scrolls >= 10:
                print("Stagnant for 10 scrolls. Stopping scroll.")
                break

            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(scroll_pause_seconds)

        # Now visit articles to fetch published_at and apply 2-year cutoff.
        results: List[Item] = []
        urls = list(seen.keys())
        print("Visiting articles for timestamps:", len(urls))

        for idx, url in enumerate(urls, start=1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                html = page.content()
                published_at = _parse_published_at_from_article_html(html)
            except PlaywrightTimeoutError:
                print("TIMEOUT:", url)
                continue
            except Exception as e:
                print("ERROR:", url, repr(e))
                continue

            it = seen[url]
            it.published_at = published_at

            # Filter by cutoff if we have a date
            if published_at:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if dt < cutoff:
                    # older than 2 years
                    pass
                else:
                    results.append(it)
            else:
                # If date missing, keep (or drop—your choice). Keeping can help debugging.
                results.append(it)

            if idx % 25 == 0:
                print(f"Processed {idx}/{len(urls)}; kept={len(results)}")

            time.sleep(article_delay_seconds)

        browser.close()

    # Sort newest first if published_at exists
    def _sort_key(x: Item):
        if not x.published_at:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
        return datetime.fromisoformat(x.published_at.replace("Z", "+00:00"))

    results.sort(key=_sort_key, reverse=True)
    return results


if __name__ == "__main__":
    data = scrape_bt_energy_commodities_two_years(
        min_items=TARGET_MIN_ITEMS,   # ~10 pages worth
        max_scrolls=200,
        scroll_pause_seconds=2.5,
        article_delay_seconds=1.0,
        headless=True,                # set False to watch it scroll
    )
    out_path = _project_path("data", "raw", "news", "_checkbt_energy_commodities_2y_playwright.jsonl")
    _save_jsonl(data, out_path)
    print("Done:", len(data), "->", out_path)