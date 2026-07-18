# ROLE: retriever — MediaWiki API client for poewiki.net.

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from bs4 import BeautifulSoup, Tag

WIKI_API = "https://www.poewiki.net/w/api.php"
WIKI_BASE = "https://www.poewiki.net/wiki"
USER_AGENT = "PoEWikiAgent/0.1 (portfolio project)"
REQUEST_DELAY_SEC = 0.15

_SKIP_LINK_PREFIXES = (
    "Special:",
    "File:",
    "Category:",
    "Help:",
    "Template:",
    "Talk:",
    "User:",
    "Wikipedia:",
    "MediaWiki:",
)

_client: httpx.Client | None = None
_client_lock = threading.Lock()
_last_request_at = 0.0
_rate_lock = threading.Lock()


def _title_to_path(title: str) -> str:
    return title.replace(" ", "_")


def _wiki_url(path: str) -> str:
    return f"{WIKI_BASE}/{path}"


def get_http_client() -> httpx.Client:
    """Shared HTTP client (connection reuse). Safe for threaded live retrieval."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(
                timeout=30.0,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return _client


def close_http_client() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None


def polite_delay(seconds: float | None = None) -> None:
    """Small spacing between wiki calls (shared across threads)."""
    global _last_request_at
    if seconds is None:
        try:
            from poe_agent.harness.config import get_settings

            delay = float(get_settings().live_wiki_request_delay_sec)
        except Exception:
            delay = REQUEST_DELAY_SEC
    else:
        delay = max(0.0, seconds)
    with _rate_lock:
        now = time.monotonic()
        wait = delay - (now - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _api_get(params: dict) -> dict:
    polite_delay()
    resp = get_http_client().get(WIKI_API, params=params)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("info", "Wiki API error"))
    return data


def _table_to_text(table: Tag) -> str:
    """Flatten a wiki table into readable lines (keeps god lists etc.)."""
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = [
            c.get_text(" ", strip=True)
            for c in tr.find_all(["th", "td"])
            if c.get_text(strip=True)
        ]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def html_to_text(html: str, *, structure_aware: bool = True) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select("table.navbox, .mw-editsection, script, style"):
        tag.decompose()

    if structure_aware:
        for table in list(soup.find_all("table")):
            flat = _table_to_text(table)
            replacement = soup.new_string(f"\n{flat}\n" if flat else "")
            table.replace_with(replacement)

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_nav_chrome(soup: BeautifulSoup) -> None:
    """Remove sidebar/nav chrome so link harvest sees content (and content tables) first."""
    for sel in (
        "table.navbox",
        "table.vertical-navbox",
        "table.infobox",
        ".mw-editsection",
        "script",
        "style",
        "#toc",
        ".toc",
        ".sidebar",
        ".navbox",
        ".vertical-navbox",
    ):
        for tag in soup.select(sel):
            tag.decompose()


def _href_to_wiki_title(href: str) -> str | None:
    if not href.startswith("/wiki/"):
        return None
    path = href.split("/wiki/", 1)[-1].split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None
    if any(path.startswith(p) or path.startswith(p.replace(":", "%3A")) for p in _SKIP_LINK_PREFIXES):
        return None
    title = path.replace("_", " ")
    if ":" in title and title.split(":", 1)[0] in {
        "Special",
        "File",
        "Category",
        "Help",
        "Template",
        "Talk",
        "User",
    }:
        return None
    return title


def extract_wiki_link_titles(
    html: str,
    *,
    max_links: int = 120,
    prefer_table_links: bool = True,
) -> list[str]:
    """
    Outgoing article titles from parse HTML (for cheap multi-hop).

    Strips nav/infobox chrome first. When prefer_table_links, content-table links
    are listed before other body links so Pantheon god tables beat early nav noise.
    """
    soup = BeautifulSoup(html, "lxml")
    _strip_nav_chrome(soup)

    table_titles: list[str] = []
    body_titles: list[str] = []
    seen: set[str] = set()

    def _add(bucket: list[str], title: str) -> None:
        key = title.casefold()
        if key in seen:
            return
        seen.add(key)
        bucket.append(title)

    for table in soup.find_all("table"):
        for a in table.select('a[href^="/wiki/"]'):
            title = _href_to_wiki_title(a.get("href") or "")
            if title:
                _add(table_titles, title)

    for a in soup.select('a[href^="/wiki/"]'):
        title = _href_to_wiki_title(a.get("href") or "")
        if title:
            _add(body_titles, title)

    if prefer_table_links:
        ordered = table_titles + body_titles
    else:
        # Body walk already includes table links in DOM order when not preferring.
        ordered = body_titles
    return ordered[: max(1, max_links)]


def fetch_page_payload(
    title: str,
    path: str | None = None,
    *,
    use_extracts: bool = False,
    structure_aware: bool = True,
    link_harvest_max: int | None = None,
    prefer_table_links: bool = True,
) -> tuple[str, str, list[str]]:
    """Return (plain_text, wiki_url, outgoing_wiki_titles)."""
    page_path = path or _title_to_path(title)
    page_name = page_path.replace("_", " ")
    links: list[str] = []

    if use_extracts and not structure_aware:
        data = _api_get(
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": "1",
                "exsectionformat": "plain",
                "titles": page_name,
                "format": "json",
                "formatversion": "2",
            }
        )
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            raise RuntimeError(f"Wiki page missing: {page_name}")
        text = (pages[0].get("extract") or "").strip()
        return text, _wiki_url(page_path), links

    data = _api_get(
        {
            "action": "parse",
            "page": page_name,
            "prop": "text",
            "format": "json",
            "formatversion": "2",
        }
    )
    html = data["parse"]["text"]
    max_links = link_harvest_max if link_harvest_max is not None else 120
    links = extract_wiki_link_titles(
        html,
        max_links=max_links,
        prefer_table_links=prefer_table_links,
    )
    text = html_to_text(html, structure_aware=structure_aware)
    return text, _wiki_url(page_path), links


def fetch_page_text(title: str, path: str | None = None) -> tuple[str, str]:
    """Return (plain_text, wiki_url) via MediaWiki API."""
    from poe_agent.harness.config import get_settings

    s = get_settings()
    text, url, _ = fetch_page_payload(
        title,
        path,
        use_extracts=s.live_wiki_use_extracts,
        structure_aware=s.live_wiki_structure_aware,
        link_harvest_max=s.live_wiki_link_harvest_max,
        prefer_table_links=s.live_wiki_prefer_table_links,
    )
    return text, url


def page_exists(title: str) -> tuple[str, str] | None:
    """Return (title, path) if the wiki page exists, else None."""
    try:
        fetch_page_text(title, _title_to_path(title))
        path = _title_to_path(title)
        return title, path
    except Exception:
        return None


def search_wiki_titles(query: str, limit: int = 8) -> list[tuple[str, str]]:
    """Search poewiki; return list of (title, path) pairs."""
    data = _api_get(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
    )
    hits: list[tuple[str, str]] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "").strip()
        if not title:
            continue
        hits.append((title, _title_to_path(title)))
    return hits


def parallel_map(fn, items: list, *, max_workers: int) -> list:
    """Run fn over items with a thread pool; preserve input order."""
    if not items:
        return []
    workers = max(1, min(max_workers, len(items)))
    if workers == 1 or len(items) == 1:
        return [fn(x) for x in items]
    results: list = [None] * len(items)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, item): i for i, item in enumerate(items)}
        for fut in as_completed(futures):
            i = futures[fut]
            results[i] = fut.result()
    return results
