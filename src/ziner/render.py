"""Template rendering and PDF generation."""

from __future__ import annotations

from datetime import date
from io import BytesIO
import math
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pypdf import PdfReader, PdfWriter, Transformation

from ziner.layout import LayoutArticle, TocEntry

TEMPLATE_DIR = Path(__file__).with_name("templates")


def _ordinal_day(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _display_date(issue_date: date) -> str:
    return f"{_ordinal_day(issue_date.day)} {issue_date.strftime('%B %Y')}"


def render_html(
    *,
    title: str,
    issue_date: date,
    articles: list[LayoutArticle],
    toc: list[TocEntry],
) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("zine.html")
    return template.render(
        title=title,
        issue_date=issue_date,
        issue_date_display=_display_date(issue_date),
        articles=articles,
        toc=toc,
    )


def build_toc(articles: list[LayoutArticle]) -> list[TocEntry]:
    return [
        TocEntry(
            title=item.article.title,
            author=item.article.author,
            site_name=item.article.site_name,
            word_count=item.word_count,
            is_truncated=item.is_truncated,
        )
        for item in articles
    ]


def check_pdf_dependencies() -> tuple[bool, str | None]:
    """Return whether the PDF backend is available on this machine."""
    try:
        from weasyprint import HTML as _HTML  # noqa: F401
    except OSError:
        return (
            False,
            "Missing native WeasyPrint libraries. On macOS, install them with "
            "`brew install pango gdk-pixbuf libffi`.",
        )
    except ImportError as exc:
        return False, f"Missing Python PDF dependency: {exc}. Run `uv sync`."

    return True, None


def count_rendered_pages(
    *,
    title: str,
    issue_date: date,
    articles: list[LayoutArticle],
) -> int:
    from weasyprint import HTML

    html = render_html(
        title=title,
        issue_date=issue_date,
        articles=articles,
        toc=build_toc(articles),
    )
    document = HTML(string=html, base_url=str(TEMPLATE_DIR)).render()
    return len(document.pages)


def booklet_sheet_count(logical_page_count: int) -> int:
    """Return the number of physical sheets needed for booklet imposition."""
    return math.ceil(logical_page_count / 4)


def booklet_side_count(logical_page_count: int) -> int:
    """Return the number of imposed PDF pages (sheet sides) after padding."""
    return booklet_sheet_count(logical_page_count) * 2


def fit_articles_to_page_limit(
    *,
    title: str,
    issue_date: date,
    articles: list[LayoutArticle],
    max_sheets: int,
) -> tuple[list[LayoutArticle], list[TocEntry], int]:
    """Keep oldest-first articles that fit within the actual rendered sheet limit."""
    selected: list[LayoutArticle] = []
    max_pages = max_sheets * 4
    page_count = count_rendered_pages(title=title, issue_date=issue_date, articles=selected)

    for article in articles:
        candidate = [*selected, article]
        candidate_pages = count_rendered_pages(
            title=title,
            issue_date=issue_date,
            articles=candidate,
        )
        if candidate_pages <= max_pages:
            selected = candidate
            page_count = candidate_pages

    return selected, build_toc(selected), page_count


def _render_logical_pdf_bytes(
    *,
    title: str,
    issue_date: date,
    articles: list[LayoutArticle],
    toc: list[TocEntry],
) -> bytes:
    from weasyprint import HTML

    html = render_html(title=title, issue_date=issue_date, articles=articles, toc=toc)
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def _zine_spreads(page_count: int) -> list[tuple[int, int]]:
    spreads: list[tuple[int, int]] = []
    left = page_count - 1
    right = 0

    while left > right:
        spreads.append((left, right))
        right += 1
        left -= 1
        if left > right:
            spreads.append((right, left))
            right += 1
            left -= 1

    return spreads


def _impose_booklet(pdf_bytes: bytes) -> bytes:
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    source_pages = list(reader.pages)

    if not source_pages:
        return pdf_bytes

    logical_width = float(source_pages[0].mediabox.width)
    logical_height = float(source_pages[0].mediabox.height)

    while len(source_pages) % 4:
        source_pages.append(None)

    for left_index, right_index in _zine_spreads(len(source_pages)):
        sheet = writer.add_blank_page(width=logical_width * 2, height=logical_height)

        left_page = source_pages[left_index]
        if left_page is not None:
            sheet.merge_transformed_page(left_page, Transformation().translate(0, 0))

        right_page = source_pages[right_index]
        if right_page is not None:
            sheet.merge_transformed_page(
                right_page,
                Transformation().translate(logical_width, 0),
            )

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def render_pdf(
    *,
    output_path: str | Path,
    title: str,
    issue_date: date,
    articles: list[LayoutArticle],
    toc: list[TocEntry],
    fullsize: bool = False,
) -> Path:
    pdf_bytes = _render_logical_pdf_bytes(
        title=title,
        issue_date=issue_date,
        articles=articles,
        toc=toc,
    )
    if not fullsize:
        pdf_bytes = _impose_booklet(pdf_bytes)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf_bytes)
    return destination
