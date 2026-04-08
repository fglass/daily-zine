"""CLI entrypoint for ziner."""

from __future__ import annotations

from datetime import date
import os
from pathlib import Path

import click
from dotenv import load_dotenv

from ziner.feed import fetch_feed, fetch_inbox
from ziner.layout import select_articles
from ziner.render import (
    booklet_sheet_count,
    booklet_side_count,
    check_pdf_dependencies,
    fit_articles_to_page_limit,
    render_pdf,
    render_issue_html,
)


def _default_output(issue_date: date) -> str:
    return f"zine-{issue_date.isoformat()}.pdf"


@click.command()
@click.option("--max-sheets", "-s", default=5, show_default=True, type=int)
@click.option("--output", "-o", type=click.Path(path_type=Path))
@click.option("--title", default="Fred Talks", show_default=True)
@click.option(
    "--fullsize",
    is_flag=True,
    help="Write a plain sequential reading PDF instead of the imposed zine PDF.",
)
@click.option("--dry", is_flag=True, help="Show selected articles without rendering.")
def main(
    max_sheets: int, output: Path | None, title: str, fullsize: bool, dry: bool
) -> None:
    """Fetch recent Reader articles and turn them into a printable zine PDF."""
    if max_sheets < 1:
        raise click.BadParameter("--max-sheets must be at least 1.")

    load_dotenv()
    token = os.getenv("READWISE_TOKEN")

    if not token:
        raise click.ClickException(
            "Missing READWISE_TOKEN. Add it to the environment or .env."
        )

    issue_date = date.today()
    destination = output or Path(_default_output(issue_date))
    output_is_html = destination.suffix.lower() == ".html"

    max_logical_pages = max_sheets * 4
    max_imposed_sides = max_sheets * 2

    if output_is_html and fullsize:
        raise click.BadParameter("--fullsize cannot be used when writing HTML output.")

    inbox_articles = fetch_inbox(token, limit=1)
    feed_articles = fetch_feed(token)
    articles = inbox_articles + feed_articles

    selected, toc = select_articles(articles, max_sheets=max_sheets)

    dependencies_ok, dependency_error = check_pdf_dependencies()
    if not dependencies_ok and not dry and not output_is_html:
        raise click.ClickException(
            dependency_error or "PDF dependencies are unavailable."
        )

    if dependencies_ok:
        selected, toc, actual_pages = fit_articles_to_page_limit(
            issue_date=issue_date,
            articles=selected,
            max_sheets=max_sheets,
            title=title,
        )
    else:
        actual_pages = None

    if not selected:
        raise click.ClickException("No articles fit the current sheet budget.")

    if dry:
        summary = (
            f"Selected {len(selected)} article(s) for {max_sheets} sheet(s)"
            f" max ({max_logical_pages} logical pages / {max_imposed_sides} imposed sides)"
        )
        if actual_pages is not None:
            summary += (
                " (rendered: "
                f"{actual_pages} logical pages / "
                f"{booklet_side_count(actual_pages)} imposed sides / "
                f"{booklet_sheet_count(actual_pages)} sheets)"
            )
        click.echo(f"{summary}:")
        for index, item in enumerate(selected, start=1):
            author = item.article.author or item.article.site_name or "Unknown"
            click.echo(
                f"{index}. {item.article.title} — {author} [{item.word_count} words]"
            )
        return

    if output_is_html:
        render_issue_html(
            output_path=destination,
            issue_date=issue_date,
            articles=selected,
            toc=toc,
            title=title,
        )
    else:
        render_pdf(
            output_path=destination,
            issue_date=issue_date,
            articles=selected,
            toc=toc,
            title=title,
            fullsize=fullsize,
        )
    click.echo(f"Wrote {destination}")


if __name__ == "__main__":
    main()
