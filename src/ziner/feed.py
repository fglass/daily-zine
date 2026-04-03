"""Readwise Reader API client."""

from __future__ import annotations

import dataclasses
from datetime import datetime

import httpx

API_URL = "https://readwise.io/api/v3/list/"


@dataclasses.dataclass
class Article:
    id: str
    title: str
    author: str | None
    url: str
    word_count: int
    html_content: str
    created_at: datetime
    summary: str | None = None
    site_name: str | None = None


def _parse_datetime(value: str) -> datetime:
    """Parse Readwise timestamps with trailing Z suffixes."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_feed(token: str, *, max_items: int = 50) -> list[Article]:
    """Fetch the current Reader feed window and return it oldest-first."""
    headers = {"Authorization": f"Token {token}"}
    params: dict = {
        # Explicitly limit results to the Reader feed and exclude inbox/later queues.
        "location": "feed",
        "withHtmlContent": "true",
    }

    articles: list[Article] = []
    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(API_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            for doc in data.get("results", []):
                # Only include live feed entries. This excludes documents that have
                # been moved to other Reader locations such as archive or later.
                if doc.get("location") != "feed":
                    continue
                # Reader's feed can still include previously opened items. Keep only
                # unread entries so selection starts from the oldest unread article.
                if doc.get("first_opened_at") is not None:
                    continue
                html = doc.get("html_content") or ""
                if not html.strip():
                    continue
                articles.append(
                    Article(
                        id=doc["id"],
                        title=doc.get("title") or "Untitled",
                        author=doc.get("author"),
                        url=doc.get("source_url") or doc.get("url", ""),
                        word_count=doc.get("word_count") or 0,
                        html_content=html,
                        created_at=_parse_datetime(doc["created_at"]),
                        summary=doc.get("summary"),
                        site_name=doc.get("site_name"),
                    )
                )

            cursor = data.get("nextPageCursor")
            if not cursor or len(articles) >= max_items:
                break
            params["pageCursor"] = cursor

    return list(reversed(articles[:max_items]))
