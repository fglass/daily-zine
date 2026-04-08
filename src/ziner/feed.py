"""Readwise Reader API client."""

from __future__ import annotations

import dataclasses
from datetime import datetime

import httpx

READWISE_API_URL = "https://readwise.io/api/v3/list/"

MIN_INBOX_FETCH = 15
MAX_INBOX_WORDS = 3000


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


def _parse_doc(doc: dict) -> Article | None:
    """Parse a Readwise API document into an Article, or None if it should be skipped."""
    if doc.get("first_opened_at") is not None:
        return None
    html = doc.get("html_content") or ""
    if not html.strip():
        return None
    return Article(
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


def fetch_feed(token: str, *, max_items: int = 50) -> list[Article]:
    """Fetch the current Reader feed window and return it newest-first."""
    headers = {"Authorization": f"Token {token}"}
    params: dict = {
        "location": "feed",
        "withHtmlContent": "true",
    }

    articles: list[Article] = []
    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(READWISE_API_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            for doc in data.get("results", []):
                article = _parse_doc(doc)
                if article is not None:
                    articles.append(article)

            cursor = data.get("nextPageCursor")
            if not cursor or len(articles) >= max_items:
                break
            params["pageCursor"] = cursor

    return articles[:max_items]


def fetch_inbox(token: str, *, limit: int = 1) -> list[Article]:
    """Return up to *limit* unread inbox articles within the word limit."""
    headers = {"Authorization": f"Token {token}"}
    params: dict = {
        "location": "new",
        "withHtmlContent": "true",
        "limit": str(max(limit, MIN_INBOX_FETCH)),
    }

    articles: list[Article] = []
    with httpx.Client(timeout=30) as client:
        resp = client.get(READWISE_API_URL, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        for doc in data.get("results", []):
            article = _parse_doc(doc)
            if article is not None and article.word_count <= MAX_INBOX_WORDS:
                articles.append(article)
                if len(articles) >= limit:
                    break

    return articles
