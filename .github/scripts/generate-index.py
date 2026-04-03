#!/usr/bin/env python3
"""Generate a simple GitHub Pages index for published zines."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import re
import sys

PDF_RE = re.compile(r"^zine-(\d{4}-\d{2}-\d{2})(-fullsize)?\.pdf$")


@dataclass(frozen=True)
class IssueFiles:
    booklet: str | None = None
    fullsize: str | None = None


def collect_issues(directory: Path) -> list[tuple[str, IssueFiles]]:
    issues: dict[str, IssueFiles] = {}

    for path in sorted(directory.glob("zine-*.pdf")):
        match = PDF_RE.fullmatch(path.name)
        if not match:
            continue

        issue_date, fullsize_suffix = match.groups()
        issue = issues.get(issue_date, IssueFiles())
        if fullsize_suffix:
            issue = IssueFiles(booklet=issue.booklet, fullsize=path.name)
        else:
            issue = IssueFiles(booklet=path.name, fullsize=issue.fullsize)
        issues[issue_date] = issue

    return sorted(issues.items(), reverse=True)


def build_html(issues: list[tuple[str, IssueFiles]]) -> str:
    items = []
    for issue_date, files in issues:
        links = []
        if files.booklet:
            links.append(
                f'<a href="{escape(files.booklet)}">booklet</a>'
            )
        if files.fullsize:
            links.append(
                f'<a href="{escape(files.fullsize)}">full size</a>'
            )
        link_markup = " · ".join(links) if links else '<span class="muted">missing files</span>'
        items.append(
            "      <li>"
            f"<span>{escape(issue_date)}</span>"
            f"<span>{link_markup}</span>"
            "</li>"
        )

    listing = "\n".join(items) if items else "      <li><span>No zines published yet.</span></li>"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Fred Talks</title>
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
        font-family: Georgia, "Times New Roman", serif;
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
      <p class="kicker">Daily archive</p>
      <h1>Fred Talks</h1>
      <p class="deck">Automated daily zines from the Readwise Reader feed. Each issue is published in booklet form for printing and a full-size version for normal reading.</p>
      <ul>
{listing}
      </ul>
    </main>
  </body>
</html>
"""


def main() -> int:
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    issues = collect_issues(output_dir)
    (output_dir / "index.html").write_text(build_html(issues), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
