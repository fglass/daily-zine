"""Article selection for print layout."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import html
import re
from typing import Any

from ziner.feed import Article

WORDS_PER_PAGE = 1000
MEDIA_BLOCK_RE = re.compile(
    r"(?is)<(video|audio|iframe|svg)\b.*?</\1>"
)
SOURCE_TAG_RE = re.compile(r"(?is)<source\b[^>]*>")
FIGURE_OPEN_RE = re.compile(r"(?is)<figure\b[^>]*>")
PICTURE_OPEN_RE = re.compile(r"(?is)<picture\b[^>]*>")
IMG_TAG_RE = re.compile(r"(?is)<img\b[^>]*>")
ALT_ATTR_RE = re.compile(r'(?is)\balt\s*=\s*["\'](.*?)["\']')
ARIA_LABEL_RE = re.compile(r'(?is)\baria-label\s*=\s*["\'](.*?)["\']')
TITLE_ATTR_RE = re.compile(r'(?is)\btitle\s*=\s*["\'](.*?)["\']')
FIGCAPTION_RE = re.compile(r"(?is)<figcaption\b[^>]*>(.*?)</figcaption>")
TAG_RE = re.compile(r"(?is)<[^>]+>")
CLASS_ATTR_RE = re.compile(r'(?is)\bclass\s*=\s*(["\'])(.*?)\1')
WHITESPACE_RE = re.compile(r"\s+")

STRONG_FOOTER_MARKERS = (
    "more reading",
    "ready for more?",
    "if you liked this post",
    "here's a preview of a related post",
    "continue reading",
    "previous ready for more?",
    "about this newsletter:",
    "update your subscription preferences",
    "unsubscribe",
    "manage your subscriber profile",
    "wikipedia daily article mailing list",
    "questions or comments? contact",
    "how did you like this issue of pointer",
    "update your email preferences or unsubscribe here",
    "click here for my youtube channel",
    "click here to explore working with me",
    "this is part of",
)
WEAK_FOOTER_MARKERS = (
    "previous",
    "subscribe",
    "restack",
    "preorder the book",
    "click here to learn more",
    "follow me on social",
    "my book recommendations this week",
    "get my popular masterclass",
    "pricing goes up in",
    "read my #1 new york times bestseller",
)
BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "div",
    "figure",
    "figcaption",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "section",
    "ul",
}
VOID_TAGS = {"br", "hr", "img", "source"}


@dataclass
class HtmlNode:
    tag: str | None
    attrs: list[tuple[str, str | None]]
    children: list["HtmlNode | str"]


def _media_marker(media_name: str, label: str | None = None) -> str:
    text = " ".join((label or "").split()).strip()
    media_name = media_name.upper()
    if text:
        return f'<p class="media-omitted">[{media_name}: {html.escape(text)}]</p>'
    return f'<p class="media-omitted">[{media_name} OMITTED]</p>'


def _strip_tags(value: str) -> str:
    return " ".join(TAG_RE.sub(" ", value).split()).strip()


def _label_from_attrs(fragment: str) -> str | None:
    for pattern in (ALT_ATTR_RE, ARIA_LABEL_RE, TITLE_ATTR_RE):
        match = pattern.search(fragment)
        if match:
            label = html.unescape(match.group(1)).strip()
            if label:
                return label
    return None


def _replace_media_block(match: re.Match[str]) -> str:
    fragment = match.group(0)
    media_name = match.group(1)
    caption_match = FIGCAPTION_RE.search(fragment)
    if caption_match:
        caption = _strip_tags(caption_match.group(1))
        if caption:
            return _media_marker(media_name, caption)
    return _media_marker(media_name, _label_from_attrs(fragment))


def _replace_media_tag(match: re.Match[str]) -> str:
    return _media_marker(match.group(1), _label_from_attrs(match.group(0)))


def _add_class(fragment: str, class_name: str) -> str:
    match = CLASS_ATTR_RE.search(fragment)
    if not match:
        return fragment[:-1] + f' class="{class_name}">'

    existing = match.group(2).split()
    if class_name in existing:
        return fragment

    updated = " ".join([*existing, class_name]).strip()
    return (
        fragment[: match.start(2)]
        + updated
        + fragment[match.end(2) :]
    )


def _compact_figure(match: re.Match[str]) -> str:
    return _add_class(match.group(0), "article-figure")


def _compact_picture(match: re.Match[str]) -> str:
    return _add_class(match.group(0), "article-picture")


def _compact_img(match: re.Match[str]) -> str:
    return _add_class(match.group(0), "article-image")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


class _FragmentTreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = HtmlNode(tag=None, attrs=[], children=[])
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag=tag, attrs=attrs, children=[])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.stack[-1].children.append(HtmlNode(tag=tag, attrs=attrs, children=[]))

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)

    def handle_entityref(self, name: str) -> None:
        self.stack[-1].children.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.stack[-1].children.append(f"&#{name};")


@dataclass(frozen=True)
class LayoutArticle:
    article: Article
    html_content: str
    word_count: int
    is_truncated: bool = False


@dataclass(frozen=True)
class TocEntry:
    title: str
    author: str | None
    site_name: str | None
    word_count: int
    is_truncated: bool = False


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return " ".join(parser.get_text().split()).strip()


def count_words(text: str) -> int:
    return len([part for part in text.split(" ") if part])


def estimate_words_from_html(html: str) -> int:
    return count_words(html_to_text(html))


def _serialize_node(node: HtmlNode | str) -> str:
    if isinstance(node, str):
        return node

    if node.tag is None:
        return "".join(_serialize_node(child) for child in node.children)

    attrs = "".join(
        f' {name}' if value is None else f' {name}="{html.escape(value, quote=True)}"'
        for name, value in node.attrs
    )
    if node.tag in VOID_TAGS:
        return f"<{node.tag}{attrs}/>"
    return (
        f"<{node.tag}{attrs}>"
        + "".join(_serialize_node(child) for child in node.children)
        + f"</{node.tag}>"
    )


def _node_text(node: HtmlNode | str) -> str:
    if isinstance(node, str):
        return html.unescape(node)
    return "".join(_node_text(child) for child in node.children)


def _normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip().lower()


def _footer_score(text: str) -> int:
    score = 0
    for marker in STRONG_FOOTER_MARKERS:
        if marker in text:
            score += 3
    for marker in WEAK_FOOTER_MARKERS:
        if marker in text:
            score += 1
    return score


def _is_empty_node(node: HtmlNode | str) -> bool:
    if isinstance(node, str):
        return not node.strip()
    if node.tag in {"br", "hr"}:
        return True
    return all(_is_empty_node(child) for child in node.children)


def _is_footer_block(node: HtmlNode | str) -> bool:
    if isinstance(node, str):
        return not node.strip()

    text = _normalize_text(_node_text(node))
    if not text:
        return node.tag in {"div", "figure", "hr", "p", "section"}

    if node.tag in {"div", "section", "article", "aside", "footer"}:
        non_empty_children = [
            child
            for child in node.children
            if not _is_empty_node(child)
        ]
        if len(non_empty_children) > 3:
            return False

    score = _footer_score(text)
    if score >= 3:
        return True
    if score >= 2 and len(text) < 700:
        return True
    if score >= 1 and len(text) < 180 and node.tag in {"p", "div", "li"}:
        return True
    return False


def _trim_footer_children(children: list[HtmlNode | str]) -> tuple[list[HtmlNode | str], bool]:
    trimmed = list(children)
    changed = False

    while trimmed and _is_empty_node(trimmed[-1]):
        trimmed.pop()
        changed = True

    while trimmed:
        last = trimmed[-1]
        if _is_footer_block(last):
            trimmed.pop()
            changed = True
            while trimmed and _is_empty_node(trimmed[-1]):
                trimmed.pop()
            continue

        if isinstance(last, HtmlNode) and last.tag in {"div", "section", "article", "aside", "footer"}:
            nested_children, nested_changed = _trim_footer_children(last.children)
            if nested_changed:
                last.children = nested_children
                changed = True
                if _is_empty_node(last):
                    trimmed.pop()
                    continue
        break

    return trimmed, changed


def trim_trailing_boilerplate(fragment: str) -> str:
    """Remove repeated CTA and newsletter footer blocks from the end only."""
    parser = _FragmentTreeBuilder()
    parser.feed(fragment)
    parser.close()

    parser.root.children, _ = _trim_footer_children(parser.root.children)
    return _serialize_node(parser.root)


def compact_media(html: str) -> str:
    """Keep images while constraining them for print-friendly layout."""
    without_blocks = MEDIA_BLOCK_RE.sub(_replace_media_block, html)
    without_sources = SOURCE_TAG_RE.sub("", without_blocks)
    with_figures = FIGURE_OPEN_RE.sub(_compact_figure, without_sources)
    with_pictures = PICTURE_OPEN_RE.sub(_compact_picture, with_figures)
    return IMG_TAG_RE.sub(_compact_img, with_pictures)


def select_articles(
    articles: list[Article],
    *,
    max_sheets: int,
    words_per_page: int = WORDS_PER_PAGE,
) -> tuple[list[LayoutArticle], list[TocEntry]]:
    """Select articles that fit within the sheet budget (newest-first)."""
    budget_words = (max_sheets * 4) * words_per_page
    remaining_words = budget_words
    selected: list[LayoutArticle] = []

    for article in articles:
        cleaned_html = trim_trailing_boilerplate(compact_media(article.html_content))
        article_words = article.word_count or estimate_words_from_html(cleaned_html)
        if remaining_words <= 0:
            break
        if article_words <= 0:
            continue

        if article_words <= remaining_words:
            selected.append(
                LayoutArticle(
                    article=article,
                    html_content=cleaned_html,
                    word_count=article_words,
                )
            )
            remaining_words -= article_words
        # Oversized articles are skipped so later shorter pieces can still fit.

    toc = [
        TocEntry(
            title=item.article.title,
            author=item.article.author,
            site_name=item.article.site_name,
            word_count=item.word_count,
            is_truncated=item.is_truncated,
        )
        for item in selected
    ]
    return selected, toc
