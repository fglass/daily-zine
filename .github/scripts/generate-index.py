#!/usr/bin/env python3
"""Generate a simple GitHub Pages index for published zines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re
import sys

ISSUE_FILE_RE = re.compile(r"^zine-(\d{4}-\d{2}-\d{2})(-fullsize)?\.(html|pdf)$")


@dataclass(frozen=True)
class IssueFiles:
    zine: str | None = None
    fullsize: str | None = None
    html: str | None = None


def collect_issues(directory: Path) -> list[tuple[str, IssueFiles]]:
    issues: dict[str, IssueFiles] = {}

    for path in sorted(directory.glob("zine-*.*")):
        match = ISSUE_FILE_RE.fullmatch(path.name)
        if not match:
            continue

        issue_date, fullsize_suffix, extension = match.groups()
        issue = issues.get(issue_date, IssueFiles())
        if extension == "html":
            issue = IssueFiles(
                html=path.name,
                zine=issue.zine,
                fullsize=issue.fullsize,
            )
        elif fullsize_suffix:
            issue = IssueFiles(
                html=issue.html,
                zine=issue.zine,
                fullsize=path.name,
            )
        else:
            issue = IssueFiles(
                html=issue.html,
                zine=path.name,
                fullsize=issue.fullsize,
            )
        issues[issue_date] = issue

    return sorted(issues.items(), reverse=True)


def build_html(issues: list[tuple[str, IssueFiles]], title: str = "Fred Talks") -> str:
    items = []
    for issue_date, files in issues:
        links = []

        if files.zine:
            links.append(f'<a href="{escape(files.zine)}">zine</a>')
        if files.fullsize:
            links.append(f'<a href="{escape(files.fullsize)}">full</a>')
        if files.html:
            links.append(f'<a href="{escape(files.html)}">html</a>')
        link_markup = (
            " · ".join(links) if links else '<span class="muted">missing files</span>'
        )
        items.append(
            "      <li>"
            f"<span>{escape(issue_date)}</span>"
            f"<span>{link_markup}</span>"
            "</li>"
        )

    listing = (
        "\n".join(items)
        if items
        else "      <li><span>No zines published yet.</span></li>"
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <link rel="alternate" type="application/rss+xml" title="{escape(title)} RSS" href="feed.xml">
    <style>
      :root {{
        color-scheme: light;
        --bg: #f3efe4;
        --paper: rgba(255, 252, 245, 0.9);
        --ink: #1e1b18;
        --muted: #6f665f;
        --rule: rgba(30, 27, 24, 0.14);
        --accent: #a33a2b;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top, rgba(163, 58, 43, 0.16), transparent 34rem),
          linear-gradient(180deg, #ede5d4 0%, var(--bg) 52%, #e8deca 100%);
        color: var(--ink);
        font-family: "Times New Roman", Times, serif;
      }}

      main {{
        width: min(52rem, calc(100vw - 2rem));
        margin: 3rem auto;
        padding: 2.5rem;
        background: var(--paper);
        border: 1px solid var(--rule);
        box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.08);
      }}

      p.kicker {{
        margin: 0 0 1rem;
        color: var(--accent);
        font: 600 0.82rem/1.2 "Helvetica Neue", Helvetica, Arial, sans-serif;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }}

      h1 {{
        margin: 0;
        font-size: clamp(2.8rem, 8vw, 5.5rem);
        line-height: 0.94;
      }}

      p.deck {{
        max-width: 40rem;
        margin: 1rem 0 2rem;
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.6;
      }}

      ul {{
        list-style: none;
        margin: 0;
        padding: 0;
        border-top: 1px solid var(--rule);
      }}

      li {{
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 1rem 0;
        border-bottom: 1px solid var(--rule);
      }}

      li span:first-child {{
        font-weight: 600;
      }}

      a {{
        color: inherit;
        text-decoration-thickness: 0.08em;
        text-underline-offset: 0.14em;
      }}

      a:hover {{
        color: var(--accent);
      }}

      .muted {{
        color: var(--muted);
      }}

      @media (max-width: 640px) {{
        main {{
          margin: 1rem auto;
          padding: 1.25rem;
        }}

        li {{
          flex-direction: column;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <p class="kicker">Daily archive · <a href="feed.xml">RSS</a></p>
      <h1>{escape(title).upper().replace(" ", "<br>")}</h1>
      <p class="deck">Automated daily zines curated from my feed.</p>
      <ul>
{listing}
      </ul>
    </main>
  </body>
</html>
"""


def build_rss(
    issues: list[tuple[str, IssueFiles]], base_url: str, title: str = "Fred Talks"
) -> str:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    items = []
    for issue_date, files in issues:
        artifact = files.html or files.fullsize or files.zine

        if not artifact:
            continue

        pub_date = (
            datetime.strptime(issue_date, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .strftime("%a, %d %b %Y %H:%M:%S %z")
        )
        link = f"{base_url}{artifact}"
        items.append(
            f"    <item>\n"
            f"      <title>Daily Read - {escape(issue_date)}</title>\n"
            f"      <link>{link}</link>\n"
            f'      <guid isPermaLink="true">{link}</guid>\n'
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"    </item>"
        )
    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(title)}</title>
    <link>{escape(base_url)}</link>
    <description>Automated daily reads.</description>
    <lastBuildDate>{now}</lastBuildDate>
{items_xml}
  </channel>
</rss>
"""


def main() -> int:
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    base_url = sys.argv[2] if len(sys.argv) > 2 else ""
    title = sys.argv[3] if len(sys.argv) > 3 else "Fred Talks"
    output_dir.mkdir(parents=True, exist_ok=True)

    issues = collect_issues(output_dir)
    (output_dir / "index.html").write_text(build_html(issues, title), encoding="utf-8")

    if base_url:
        (output_dir / "feed.xml").write_text(
            build_rss(issues, base_url, title), encoding="utf-8"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
