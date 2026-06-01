# ROLE: retriever — MediaWiki API client for poewiki.net.

from __future__ import annotations

import re
import time

import httpx
from bs4 import BeautifulSoup

WIKI_API = "https://www.poewiki.net/w/api.php"
WIKI_BASE = "https://www.poewiki.net/wiki"
USER_AGENT = "PoEWikiAgent/0.1 (portfolio project)"
REQUEST_DELAY_SEC = 0.35


def _title_to_path(title: str) -> str:
    return title.replace(" ", "_")


def _wiki_url(path: str) -> str:
    return f"{WIKI_BASE}/{path}"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select("table.navbox, .mw-editsection, script, style"):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_page_text(title: str, path: str | None = None) -> tuple[str, str]:
    """Return (plain_text, wiki_url) via MediaWiki parse API."""
    page_path = path or _title_to_path(title)
    params = {
        "action": "parse",
        "page": page_path.replace("_", " "),
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(WIKI_API, params=params)
        resp.raise_for_status()
        data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("info", "Wiki API error"))
    html = data["parse"]["text"]
    return html_to_text(html), _wiki_url(page_path)


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
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    }
    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(WIKI_API, params=params)
        resp.raise_for_status()
        data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("info", "Wiki API error"))

    hits: list[tuple[str, str]] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "").strip()
        if not title:
            continue
        hits.append((title, _title_to_path(title)))
    return hits


def polite_delay() -> None:
    time.sleep(REQUEST_DELAY_SEC)
