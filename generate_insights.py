#!/usr/bin/env python3
"""Build local Insights and blog pages from existing on-disk article HTML.

The generator treats the checked-in article pages under insights/YYYY/M/D/*.html
as the source of truth and rewrites index, tag, and article pages using the
shared site shell. No git-history lookups are used.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from html import escape, unescape
from pathlib import Path
from urllib.parse import urlparse

import components

ROOT = Path(__file__).resolve().parent

PAGINATED_INDEX_ROUTE = "blog/page-2.html"
LEGACY_PAGINATED_INDEX_ROUTE = "blog/index.html?offset=1487147475880.html"
POSTS_PER_PAGE = 5
POST_THUMBNAIL_FALLBACKS = {
    "New Directions - Part 2": "assets/blog/15A0199-grey-building-blue-window-sac-palm-trees.jpg",
    "Portland Marketing - Week Two - Disorganized thoughts from disorganized marketing": "assets/blog/skyline.jpg",
}


def discover_article_paths() -> list[str]:
    """Discover article pages from the local insights tree, newest first."""

    candidates = [
        path
        for path in (ROOT / "insights").glob("*/*/*/*.html")
        if path.name != "index.html"
    ]

    def key(path: Path) -> tuple[int, int, int, str]:
        rel = path.relative_to(ROOT).as_posix().split("/")
        year, month, day = int(rel[1]), int(rel[2]), int(rel[3])
        return (year, month, day, rel[4])

    return [path.relative_to(ROOT).as_posix() for path in sorted(candidates, key=key, reverse=True)]


def fallback_thumbnail(title: str) -> str | None:
    path = POST_THUMBNAIL_FALLBACKS.get(title)
    if path and (ROOT / path).is_file():
        return path
    return None


@dataclass
class Article:
    path: str
    title: str
    date_iso: str
    date_display: str
    tags: list[tuple[str, str]]  # (tag_file, display_name)
    blocks: list
    thumbnail: str | None
    excerpt: str

    @property
    def dir(self) -> str:
        return posixpath.dirname(self.path)

    @property
    def filename(self) -> str:
        return posixpath.basename(self.path)


def parse_article(path: str) -> Article:
    text = (ROOT / path).read_text(encoding="utf-8")
    return parse_native_article(path, text)


def parse_native_article(path: str, text: str) -> Article:
    """Read a previously generated local article and normalize it."""
    title_match = re.search(r"<h1>(.*?)</h1>", text, re.S)
    title = unescape(re.sub(r"<[^>]+>", "", title_match.group(1)).strip()) if title_match else path

    time_match = re.search(r"<time datetime=\"([^\"]+)\">(.*?)</time>", text, re.S)
    date_iso = time_match.group(1) if time_match else ""
    date_display = unescape(re.sub(r"<[^>]+>", "", time_match.group(2)).strip()) if time_match else ""

    main_match = re.search(r'<main class="content-page post">(.*?)</main>', text, re.S)
    main_html = main_match.group(1) if main_match else ""
    body_start = re.search(r"</h1>\s*", main_html, re.S)
    body = main_html[body_start.end() :] if body_start else main_html

    tags: list[tuple[str, str]] = []
    tags_match = re.match(r'<p class="post-tags">Tags: (.*?)</p>\s*', body, re.S)
    if tags_match:
        for href, name in re.findall(r'<a href="([^"]+)">(.*?)</a>', tags_match.group(1), re.S):
            tags.append((posixpath.basename(urlparse(href).path), unescape(re.sub(r"<[^>]+>", "", name)).strip()))
        body = body[tags_match.end() :]

    image_match = re.search(r'<img src="([^"]+)"', body)
    thumbnail = None
    if image_match:
        thumbnail = posixpath.normpath(posixpath.join(posixpath.dirname(path), image_match.group(1)))
    if thumbnail is None:
        thumbnail = fallback_thumbnail(title)

    excerpt = ""
    first_p = re.search(r"<p(?:\s[^>]*)?>(.*?)</p>", body, re.S)
    if first_p:
        excerpt = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", first_p.group(1)))).strip()
        if len(excerpt) > 220:
            cut = excerpt.rfind(" ", 0, 217)
            excerpt = excerpt[: cut if cut > 0 else 217].rstrip() + "..."

    return Article(
        path=path,
        title=title,
        date_iso=date_iso,
        date_display=date_display,
        tags=tags,
        blocks=[("html", body.strip())] if body.strip() else [],
        thumbnail=thumbnail,
        excerpt=excerpt,
    )


def rel(from_dir: str, target: str) -> str:
    if from_dir in ("", "."):
        return target
    return posixpath.relpath(target, from_dir)


def _prefix(from_dir: str) -> str:
    if from_dir in ("", "."):
        return ""
    return posixpath.relpath(".", from_dir) + "/"


def page_shell(title: str, description: str, from_dir: str, insights_current: bool, main_html: str) -> str:
    return components.document(
        title=title,
        description=description,
        body=main_html,
        active="insights/" if insights_current else "",
        prefix=_prefix(from_dir),
    )


def render_article_body(article: Article, from_dir: str) -> str:
    parts = []
    for kind, payload in article.blocks:
        if kind == "html" and payload:
            html = payload
            html = re.sub(
                r'src="([^":]+(?:/[^":]*)?)"',
                lambda m: f'src="{rel(from_dir, posixpath.normpath(posixpath.join(posixpath.dirname(article.path), m.group(1))))}"',
                html,
            )
            parts.append(f"    {html}")
    return "\n".join(p for p in parts if p.strip())


def render_tags_line(article: Article, from_dir: str) -> str:
    if not article.tags:
        return ""
    links = ", ".join(
        f'<a href="{rel(from_dir, "insights/tag/" + tag_file)}">{escape(name)}</a>' for tag_file, name in article.tags
    )
    return f'    <p class="post-tags">Tags: {links}</p>\n'


def render_article_page(article: Article) -> str:
    from_dir = article.dir
    body = render_article_body(article, from_dir)
    tags_line = render_tags_line(article, from_dir)
    main = f"""  <main class="content-page post">
    <p class="post-meta"><time datetime="{escape(article.date_iso, quote=True)}">{escape(article.date_display)}</time></p>
    <h1>{escape(article.title)}</h1>
{tags_line}{body}
  </main>"""
    return page_shell(article.title, f"{article.title} - Insights by Ryan Filgas", from_dir, True, main)


def render_post_card(article: Article, from_dir: str) -> str:
    href = rel(from_dir, article.path)
    if not article.thumbnail:
        return ""
    return f"""      <li class="post-card">
        <a href="{href}" class="post-gallery-link">
          <img src="{rel(from_dir, article.thumbnail)}" alt="" loading="lazy">
          <time class="post-gallery-date" datetime="{escape(article.date_iso, quote=True)}">{escape(article.date_display)}</time>
          <span class="post-gallery-title">{escape(article.title)}</span>
        </a>
      </li>"""


def render_post_list(articles: list[Article], from_dir: str) -> str:
    cards = "\n".join(card for article in articles if (card := render_post_card(article, from_dir)))
    return f'    <ul class="post-list">\n{cards}\n    </ul>'


def render_tag_cloud(all_tags: list[tuple[str, str]], from_dir: str) -> str:
    chips = "\n".join(
        f'      <li><a href="{rel(from_dir, "insights/tag/" + tag_file)}">{escape(name)}</a></li>'
        for tag_file, name in all_tags
    )
    return f"""    <section class="tag-cloud">
      <h2>Browse by Tag</h2>
      <ul>
{chips}
      </ul>
    </section>"""


def render_index_page(
    articles: list[Article],
    all_tags: list[tuple[str, str]],
    title: str,
    from_dir: str = ".",
    previous_href: str | None = None,
    next_href: str | None = None,
) -> str:
    intro = (
        "<p>Notes on photography, art, and the occasional software engineering detour "
        "- a running log from Ryan Filgas.</p>"
    )
    pagination = ""
    if previous_href or next_href:
        links = []
        if previous_href:
            links.append(f'<a href="{rel(from_dir, previous_href)}">Previous</a>')
        if next_href:
            links.append(f'<a href="{rel(from_dir, next_href)}">Next</a>')
        links_html = "\n      ".join(links)
        pagination = f"""    <nav class="post-pagination" aria-label="Insights pages">
      {links_html}
    </nav>
"""

    main = f"""  <main class="content-page post-index">
    <h1>{escape(title)}</h1>
    {intro}
{render_post_list(articles, from_dir)}
{pagination}
{render_tag_cloud(all_tags, from_dir)}
  </main>"""
    return page_shell(title, "Insights - photography, art, and software engineering notes by Ryan Filgas", from_dir, True, main)


def render_tag_page(tag_name: str, matching: list[Article], from_dir: str) -> str:
    title = f"Tag: {tag_name}"
    main = f"""  <main class="content-page post-index">
    <h1>{escape(title)}</h1>
    <p><a href="{rel(from_dir, 'insights/')}">&#8592; All Insights</a></p>
{render_post_list(matching, from_dir)}
  </main>"""
    return page_shell(title, f"Insights posts tagged {tag_name} - Ryan Filgas", from_dir, True, main)


def main() -> None:
    article_paths = discover_article_paths()
    if not article_paths:
        raise ValueError("No local insights article pages found")

    articles = [parse_article(path) for path in article_paths]

    for article in articles:
        out_path = ROOT / article.path
        out_path.write_text(render_article_page(article), encoding="utf-8")

    tag_registry: dict[str, tuple[str, list[Article]]] = {}
    for article in articles:
        for tag_file, name in article.tags:
            if tag_file not in tag_registry:
                tag_registry[tag_file] = (name, [])
            tag_registry[tag_file][1].append(article)

    all_tags = [(tag_file, name) for tag_file, (name, _) in tag_registry.items()]

    first_page = articles[:POSTS_PER_PAGE]
    second_page = articles[POSTS_PER_PAGE:]

    index_html = render_index_page(first_page, all_tags, "Insights", "insights", None, PAGINATED_INDEX_ROUTE if second_page else None)
    (ROOT / "insights" / "index.html").write_text(index_html, encoding="utf-8")
    blog_html = render_index_page(first_page, all_tags, "Blog", "blog", None, PAGINATED_INDEX_ROUTE if second_page else None)
    (ROOT / "blog" / "index.html").write_text(blog_html, encoding="utf-8")
    page2_html = render_index_page(second_page, all_tags, "Blog", "blog", "insights/", None)
    (ROOT / PAGINATED_INDEX_ROUTE).write_text(page2_html, encoding="utf-8")

    legacy_offset_path = ROOT / LEGACY_PAGINATED_INDEX_ROUTE
    if legacy_offset_path.exists() and LEGACY_PAGINATED_INDEX_ROUTE != PAGINATED_INDEX_ROUTE:
        legacy_offset_path.unlink()

    for tag_file, (name, matching) in tag_registry.items():
        out_path = ROOT / "insights" / "tag" / tag_file
        page = render_tag_page(name, matching, "insights/tag")
        out_path.write_text(page, encoding="utf-8")

    forbidden = ("typekit", "google fonts", "cdn.jsdelivr")
    generated_paths = (
        [ROOT / a.path for a in articles]
        + [ROOT / "insights" / "index.html", ROOT / "blog" / "index.html", ROOT / PAGINATED_INDEX_ROUTE]
        + [ROOT / "insights" / "tag" / t for t in tag_registry]
    )
    for path in generated_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in ("http://", "https://"):
            for match in re.finditer(re.escape(token) + r"[^\"'\s<>]+", lowered):
                url = match.group(0)
                if "youtube.com" in url or "linkedin.com" in url or "github.com" in url or "mailto:" in url:
                    continue
                raise ValueError(f"{path}: unexpected remote reference: {url}")
        if any(term in lowered for term in forbidden):
            raise ValueError(f"{path}: forbidden remote reference present")

    print(f"Articles rewritten: {len(articles)}")
    print(f"Tag pages rewritten: {len(tag_registry)}")
    print("Index pages rewritten: 3 (insights/, blog/, page-2 route)")


if __name__ == "__main__":
    main()
