"""
Indeed RSS job ingestion — Week 1 proof that we can pull real job listings.

Uses the feedparser library to read a public RSS feed — no scraping, no login.

NOTE (2025+): Indeed has largely discontinued public RSS feeds. Many regions
return HTTP 403 or an HTML job-search page instead of XML. If that happens,
this script explains the issue clearly. For Week 1 demos, you can temporarily
point INDEED_RSS_URL at any working public job RSS (see README troubleshooting).

Edit INDEED_RSS_URL below, then run:
    python agents/indeed_rss.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import feedparser

# Browser-like User-Agent — some servers block the default Python client.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; career-agent/1.0; +https://github.com/local/career-agent)"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ---------------------------------------------------------------------------
# EDIT THIS URL to match your job search
# ---------------------------------------------------------------------------
INDEED_RSS_URL = "https://in.indeed.com/rss?q=python+developer&l=Bangalore"


def _fetch_feed_bytes(feed_url: str) -> bytes:
    """Download raw feed bytes with a proper User-Agent header."""
    request = Request(feed_url, headers=REQUEST_HEADERS)
    try:
        with urlopen(request, timeout=20) as response:
            return response.read()
    except HTTPError as exc:
        if exc.code == 403:
            raise ValueError(
                "Indeed returned HTTP 403 Forbidden for this RSS URL.\n"
                "Indeed no longer reliably offers public RSS feeds for automated "
                "access in many regions.\n"
                "Week 1 Gmail ingestion still works; for RSS demos, try another "
                "public job feed (see README troubleshooting) or test the URL in "
                "an RSS reader first."
            ) from exc
        raise ValueError(
            f"HTTP error while fetching feed: {exc.code} {exc.reason}\n"
            f"URL: {feed_url}"
        ) from exc
    except URLError as exc:
        raise ValueError(
            f"Network error while fetching feed: {exc.reason}\n"
            f"URL: {feed_url}"
        ) from exc


def parse_indeed_feed(feed_url: str = INDEED_RSS_URL) -> feedparser.FeedParserDict:
    """
    Fetch and parse an Indeed RSS feed.

    Args:
        feed_url: Full Indeed RSS URL for your search.

    Returns:
        feedparser result object (check result.entries for job listings).

    Raises:
        ValueError: If the feed cannot be parsed or returns no entries.
    """
    print(f"Fetching Indeed RSS feed:\n  {feed_url}\n")

    raw = _fetch_feed_bytes(feed_url)
    preview = raw[:200].lstrip().lower()

    # Indeed often returns an HTML search page instead of RSS XML.
    if preview.startswith(b"<!doctype html") or preview.startswith(b"<html"):
        raise ValueError(
            "Indeed returned an HTML web page instead of an RSS/XML feed.\n"
            "Their public RSS endpoints are no longer reliable for scripts.\n"
            "This is not a bug in your code — Indeed changed/discontinued the feed.\n"
            "For Week 1, Gmail ingestion proves API access; pick another RSS source "
            "if you need a second live feed for your demo."
        )

    feed = feedparser.parse(raw)

    if feed.bozo and not feed.entries:
        raise ValueError(
            f"Failed to parse RSS feed: {getattr(feed, 'bozo_exception', 'unknown error')}\n"
            "Check that the URL is correct and returns XML (not HTML)."
        )

    if not feed.entries:
        raise ValueError(
            "Feed loaded but contained zero job entries.\n"
            "Try broadening your search keywords or location in INDEED_RSS_URL."
        )

    return feed


def _format_published(entry: dict) -> str:
    """Convert an RSS entry's published date to a readable string."""
    published = entry.get("published") or entry.get("updated")
    if not published:
        return "(date unknown)"

    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            dt = datetime(*parsed[:6])
            return dt.strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            pass

    return published


def print_jobs(feed: feedparser.FeedParserDict) -> None:
    """Print title, link, and published date for each job in the feed."""
    entries = feed.entries
    feed_title = feed.feed.get("title", "Indeed Jobs")

    print(f"Feed: {feed_title}")
    print(f"Found {len(entries)} job listing(s):\n")
    print("-" * 72)

    for index, entry in enumerate(entries, start=1):
        title = (entry.get("title") or "(no title)").strip()
        link = (entry.get("link") or "(no link)").strip()
        published = _format_published(entry)

        print(f"[{index}] {title}")
        print(f"     Link      : {link}")
        print(f"     Published : {published}")
        print("-" * 72)


def ingest_indeed_jobs(feed_url: str = INDEED_RSS_URL) -> list[dict]:
    """
    Main entry point: fetch RSS feed, print jobs, return entry list.

    Returns:
        List of feedparser entry dicts.
    """
    feed = parse_indeed_feed(feed_url)
    print_jobs(feed)
    return list(feed.entries)


if __name__ == "__main__":
    # Windows consoles often use cp1252; job titles/links may contain Unicode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("Indeed RSS job ingestion — Week 1 test\n")

    try:
        ingest_indeed_jobs()
    except ValueError as exc:
        print(f"\n{exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nUnexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
