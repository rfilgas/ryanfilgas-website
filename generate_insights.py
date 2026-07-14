#!/usr/bin/env python3
"""Build the native blog/Insights pages from the mirrored Squarespace source.

Reads the original mirrored markup for each page from git HEAD (so the
generator is reproducible no matter what is currently on disk) and writes
semantic, dependency-free static HTML that shares the site's native shell
(assets/native.css) with the rest of the already-converted pages.

Covers:
  * blog-insights.html, blog.html, and the mirrored offset list -> the Insights index
  * blog?tag=Carson Block.html / Frozen.html -> legacy tag routes
  * insights/tag/*.html                -> tag list routes
  * insights/*/*/*/*.html              -> individual articles
"""

from __future__ import annotations

import posixpath
import re
import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import components

ROOT = Path(__file__).resolve().parent

# The original Squarespace mirror lives in this commit; sourcing from it keeps
# the generator reproducible even after the mirror dirs are removed from disk.
MIRROR = "b20f73c"

ARTICLE_PATHS = [
    "insights/2023/11/11/2023.html",
    "insights/2021/11/19/new-beginnings-version-2.html",
    "insights/2020/2/4/portland-marketing-week-two-disorganized-thoughts-from-disorganized-marketing.html",
    "insights/2019/3/23/6-month-reflections.html",
    "insights/2019/1/1/goodbye-2018.html",
    "insights/2017/5/13/new-directions.html",
    "insights/2017/2/14/reboot.html",
    "insights/2016/4/17/the-carson-block-building.html",
    "insights/2015/9/6/i-graduated.html",
]

# Root-level legacy routes that mirrored the old "/blog?tag=" filter UI.
# The static mirror captured the same unfiltered page for every query string,
# so we rebuild them as properly filtered tag routes instead, matching the
# real tag pages under insights/tag/.
LEGACY_TAG_ROUTES = {
    "blog?tag=Carson Block.html": "Carson+Block",
    "blog?tag=Frozen.html": "Frozen",
}
PAGINATED_INDEX_ROUTE = "blog/index.html?offset=1487147475880.html"

VOID_TAGS = {"br", "img", "hr", "input", "meta", "link"}
INLINE_ALLOWED = {"p", "br", "ol", "ul", "li", "strong", "em", "b", "i", "blockquote", "a"}


def git_show(path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{MIRROR}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def git_show_bytes(path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{MIRROR}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return result.stdout


def local_image_path(url: str) -> str:
    """Copy a mirrored source image into assets/blog/. Falls back to reading the
    image bytes from the mirror commit when the working-tree copy is gone."""
    parsed = urlparse(url)
    source = Path(parsed.netloc + parsed.path)
    suffix = source.suffix.lower() or ".jpg"
    destination = Path("assets/blog") / f"{hashlib.sha256(url.encode()).hexdigest()[:16]}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not (ROOT / destination).exists():
        if (ROOT / source).is_file():
            shutil.copy2(ROOT / source, ROOT / destination)
        else:
            try:
                (ROOT / destination).write_bytes(git_show_bytes(source.as_posix()))
            except subprocess.CalledProcessError:
                raise FileNotFoundError(f"missing mirror image: {url}")
    return destination.as_posix()


def youtube_watch_url(embed_src: str) -> str:
    """Turn a protocol-relative YouTube embed src into a stable https watch URL."""
    match = re.search(r"youtube\.com/embed/([\w-]+)", embed_src)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    return "https:" + embed_src if embed_src.startswith("//") else embed_src


def alt_from_filename(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return stem


class BodyParser(HTMLParser):
    """Walks a Squarespace post body and emits an ordered list of content
    blocks: ('html', text_html) for prose, or ('images', [(src, alt), ...])
    for image/gallery blocks. A ('video', url) block is emitted for embedded
    video components, rendered later as a plain link (no remote runtime
    resource is fetched).
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, object]] = []
        self.stack: list[tuple[str, dict, int]] = []
        self.block_stack: list[dict] = []  # active sqs-block contexts

    def _current_block(self):
        return self.block_stack[-1] if self.block_stack else None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()

        if "sqs-block" in classes:
            kind = "html"
            if "gallery-block" in classes or "image-block" in classes:
                kind = "images"
            elif "video-block" in classes:
                kind = "video"
            elif "horizontalrule-block" in classes:
                kind = "rule"
            ctx = {
                "kind": kind,
                "depth": len(self.stack),
                "html": [],
                "images": [],
                "seen": set(),
                "video": None,
                "capturing": False,
                "capture_depth": None,
            }
            self.block_stack.append(ctx)

        ctx = self._current_block()
        if ctx is not None:
            if tag == "img" and "data-image" in attributes:
                url = attributes["data-image"]
                if url not in ctx["seen"]:
                    ctx["seen"].add(url)
                    ctx["images"].append((url, attributes.get("alt", "")))
            elif ctx["kind"] == "video" and tag == "div" and attributes.get("data-provider-name"):
                raw = unescape(attributes.get("data-html", ""))
                match = re.search(r'src="([^"]+)"', raw)
                if match:
                    ctx["video"] = match.group(1)
            elif ctx["kind"] == "html" and "sqs-html-content" in classes and not ctx["capturing"]:
                ctx["capturing"] = True
                ctx["capture_depth"] = len(self.stack)
            elif ctx.get("capturing") and tag in INLINE_ALLOWED:
                attr_html = ""
                if tag == "a" and "href" in attributes:
                    attr_html = f' href="{escape(attributes["href"], quote=True)}"'
                ctx["html"].append(f"<{tag}{attr_html}>")

        if tag not in VOID_TAGS:
            self.stack.append((tag, attributes, len(self.block_stack)))
        elif ctx is not None and ctx.get("capturing") and tag == "br":
            ctx["html"].append("<br>")

    def handle_endtag(self, tag):
        ctx = self._current_block()
        if ctx is not None and ctx.get("capturing") and tag in INLINE_ALLOWED:
            ctx["html"].append(f"</{tag}>")

        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

        if ctx is not None and ctx.get("capturing") and tag == "div" and len(self.stack) <= ctx["capture_depth"]:
            ctx["capturing"] = False

        if tag == "div" and self.block_stack:
            top = self.block_stack[-1]
            if len(self.stack) <= top["depth"]:
                self.block_stack.pop()
                if top["kind"] == "html" and top["html"]:
                    self.blocks.append(("html", "".join(top["html"]).strip()))
                elif top["kind"] == "images" and top["images"]:
                    self.blocks.append(("images", top["images"]))
                elif top["kind"] == "video" and top["video"]:
                    self.blocks.append(("video", top["video"]))

    def handle_data(self, data):
        ctx = self._current_block()
        if ctx is not None and ctx.get("capturing"):
            ctx["html"].append(escape(data))


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
    text = git_show(path)
    if 'class="entry-title"' not in text:
        return parse_native_article(path, text)

    title_match = re.search(r'<h1 class="entry-title">\s*<a[^>]*>([^<]*)</a>', text)
    title = unescape(title_match.group(1).strip()) if title_match else path

    time_match = re.search(r'<time datetime="([^"]+)">([^<]*)</time>', text)
    date_iso = time_match.group(1) if time_match else ""
    date_display = unescape(time_match.group(2).strip()) if time_match else ""

    tags_match = re.search(r'<span class="tags">Tags: (.*?)</span>', text)
    tags: list[tuple[str, str]] = []
    if tags_match:
        for href, name in re.findall(r'<a href="[^"]*/tag/([^"]+?)\.html#show-archive"[^>]*>([^<]+)</a>', tags_match.group(1)):
            tags.append((f"{href}.html", unescape(name)))

    body_match = re.search(r'<div class="body entry-content">(.*?)\n\s*<!--POST FOOTER-->', text, re.S)
    body_html = body_match.group(1) if body_match else ""

    parser = BodyParser()
    parser.feed(body_html)

    blocks = []
    thumbnail = None
    excerpt = ""
    for kind, payload in parser.blocks:
        if kind == "html":
            blocks.append(("html", payload))
            if not excerpt:
                first_p = re.search(r"<p[^>]*>(.*?)</p>", payload, re.S)
                if first_p:
                    plain = re.sub(r"<[^>]+>", " ", first_p.group(1))
                    plain = re.sub(r"\s+", " ", unescape(plain)).strip()
                    if plain:
                        excerpt = plain
        elif kind == "images":
            resolved = []
            for url, alt in payload:
                src = local_image_path(url)
                alt_text = unescape(alt).strip() or alt_from_filename(src)
                resolved.append((src, alt_text))
                if thumbnail is None:
                    thumbnail = src
            blocks.append(("images", resolved))
        elif kind == "video":
            blocks.append(("video", youtube_watch_url(payload)))

    if len(excerpt) > 220:
        cut = excerpt.rfind(" ", 0, 217)
        excerpt = excerpt[: cut if cut > 0 else 217].rstrip() + "\u2026"

    return Article(
        path=path,
        title=title,
        date_iso=date_iso,
        date_display=date_display,
        tags=tags,
        blocks=blocks,
        thumbnail=thumbnail,
        excerpt=excerpt,
    )


def parse_native_article(path: str, text: str) -> Article:
    """Read a previously generated article so reruns remain reproducible."""
    title_match = re.search(r"<h1>(.*?)</h1>", text, re.S)
    title = unescape(re.sub(r"<[^>]+>", "", title_match.group(1)).strip()) if title_match else path

    time_match = re.search(r"<time datetime=\"([^\"]+)\">(.*?)</time>", text, re.S)
    date_iso = time_match.group(1) if time_match else ""
    date_display = unescape(re.sub(r"<[^>]+>", "", time_match.group(2)).strip()) if time_match else ""

    main_match = re.search(r'<main class="content-page post">(.*?)</main>', text, re.S)
    main_html = main_match.group(1) if main_match else ""
    body_start = re.search(r"</h1>\s*", main_html, re.S)
    body = main_html[body_start.end():] if body_start else main_html

    tags: list[tuple[str, str]] = []
    tags_match = re.match(r'<p class="post-tags">Tags: (.*?)</p>\s*', body, re.S)
    if tags_match:
        for href, name in re.findall(r'<a href="([^"]+)">(.*?)</a>', tags_match.group(1), re.S):
            tags.append((posixpath.basename(urlparse(href).path), unescape(re.sub(r"<[^>]+>", "", name)).strip()))
        body = body[tags_match.end():]

    image_match = re.search(r'<img src="([^"]+)"', body)
    thumbnail = None
    if image_match:
        thumbnail = posixpath.normpath(posixpath.join(posixpath.dirname(path), image_match.group(1)))

    excerpt = ""
    first_p = re.search(r"<p(?:\s[^>]*)?>(.*?)</p>", body, re.S)
    if first_p:
        excerpt = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", first_p.group(1)))).strip()
        if len(excerpt) > 220:
            cut = excerpt.rfind(" ", 0, 217)
            excerpt = excerpt[: cut if cut > 0 else 217].rstrip() + "\u2026"

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


def nav_link(label, href, current):
    attribute = ' aria-current="page"' if current else ""
    return f'<a href="{href}"{attribute}>{label}</a>'


def _prefix(from_dir: str) -> str:
    if from_dir in ("", "."):
        return ""
    return posixpath.relpath(".", from_dir) + "/"


MENU_SCRIPT = ""  # menu toggle now handled by assets/gallery.js


def page_shell(title: str, description: str, from_dir: str, insights_current: bool, main_html: str) -> str:
    return components.document(
        title=title,
        description=description,
        body=main_html,
        active="blog-insights.html" if insights_current else "",
        prefix=_prefix(from_dir),
    )


def render_block_html(block_html: str) -> str:
    return block_html if block_html else ""


def render_article_body(article: Article, from_dir: str) -> str:
    parts = []
    for kind, payload in article.blocks:
        if kind == "html":
            parts.append(f"    {render_block_html(payload)}")
        elif kind == "images":
            if len(payload) == 1:
                src, alt = payload[0]
                parts.append(
                    f'    <figure class="post-figure"><img src="{rel(from_dir, src)}" alt="{escape(alt, quote=True)}" loading="lazy"></figure>'
                )
            else:
                figures = "\n".join(
                    f'        <img src="{rel(from_dir, src)}" alt="{escape(alt, quote=True)}" loading="lazy">'
                    for src, alt in payload
                )
                parts.append(f'    <div class="post-gallery">\n{figures}\n    </div>')
        elif kind == "video":
            parts.append(
                f'    <p class="post-video-link">Video: <a href="{escape(payload, quote=True)}">{escape(payload)}</a></p>'
            )
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
    return page_shell(article.title, f"{article.title} \u2013 Insights by Ryan Filgas", from_dir, True, main)


def render_post_card(article: Article, from_dir: str) -> str:
    href = rel(from_dir, article.path)
    thumb = ""
    if article.thumbnail:
        thumb = f'<a href="{href}" class="post-card-thumb" tabindex="-1" aria-hidden="true"><img src="{rel(from_dir, article.thumbnail)}" alt="" loading="lazy"></a>'
    excerpt = f"<p>{escape(article.excerpt)}</p>" if article.excerpt else ""
    tags = ""
    if article.tags:
        tag_links = ", ".join(
            f'<a href="{rel(from_dir, "insights/tag/" + tag_file)}">{escape(name)}</a>' for tag_file, name in article.tags
        )
        tags = f'<p class="post-card-tags">Tags: {tag_links}</p>'
    return f"""      <li class="post-card">
        {thumb}
        <div class="post-card-body">
          <time datetime="{escape(article.date_iso, quote=True)}">{escape(article.date_display)}</time>
          <h2><a href="{href}">{escape(article.title)}</a></h2>
          {excerpt}
          {tags}
        </div>
      </li>"""


def render_post_list(articles: list[Article], from_dir: str) -> str:
    cards = "\n".join(render_post_card(article, from_dir) for article in articles)
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
    articles: list[Article], all_tags: list[tuple[str, str]], title: str, from_dir: str = "."
) -> str:
    intro = (
        "<p>Notes on photography, art, and the occasional software engineering detour "
        "\u2014 a running log from Ryan Filgas.</p>"
    )
    main = f"""  <main class="content-page post-index">
    <h1>{escape(title)}</h1>
    {intro}
{render_post_list(articles, from_dir)}
{render_tag_cloud(all_tags, from_dir)}
  </main>"""
    return page_shell(title, "Insights \u2013 photography, art, and software engineering notes by Ryan Filgas", from_dir, True, main)


def render_tag_page(tag_file: str, tag_name: str, matching: list[Article], from_dir: str) -> str:
    title = f"Tag: {tag_name}"
    main = f"""  <main class="content-page post-index">
    <h1>{escape(title)}</h1>
    <p><a href="{rel(from_dir, 'blog-insights.html')}">\u2190 All Insights</a></p>
{render_post_list(matching, from_dir)}
  </main>"""
    return page_shell(title, f"Insights posts tagged {tag_name} \u2013 Ryan Filgas", from_dir, True, main)


def main():
    articles = [parse_article(path) for path in ARTICLE_PATHS]

    # Write article pages in place.
    for article in articles:
        out_path = ROOT / article.path
        out_path.write_text(render_article_page(article), encoding="utf-8")

    # Build the tag registry (tag file -> (display name, matching articles)) from
    # the article data itself, in first-seen order.
    tag_registry: dict[str, tuple[str, list[Article]]] = {}
    for article in articles:
        for tag_file, name in article.tags:
            if tag_file not in tag_registry:
                tag_registry[tag_file] = (name, [])
            tag_registry[tag_file][1].append(article)

    all_tags = [(tag_file, name) for tag_file, (name, _) in tag_registry.items()]

    # Insights index routes share the same generated listing.  The offset
    # filename is a crawler artifact; blog.html is its GitHub Pages-safe route.
    index_html = render_index_page(articles, all_tags, "Insights")
    (ROOT / "blog-insights.html").write_text(index_html, encoding="utf-8")
    blog_html = render_index_page(articles, all_tags, "Blog")
    (ROOT / "blog.html").write_text(blog_html, encoding="utf-8")
    offset_html = render_index_page(articles, all_tags, "Blog", "blog")
    (ROOT / PAGINATED_INDEX_ROUTE).write_text(offset_html, encoding="utf-8")

    # Tag list routes.
    for tag_file, (name, matching) in tag_registry.items():
        out_path = ROOT / "insights" / "tag" / tag_file
        page = render_tag_page(tag_file, name, matching, "insights/tag")
        out_path.write_text(page, encoding="utf-8")

    # Legacy root-level tag routes, now correctly filtered.
    for filename, tag_slug in LEGACY_TAG_ROUTES.items():
        name, matching = tag_registry[f"{tag_slug}.html"]
        page = render_tag_page(f"{tag_slug}.html", name, matching, ".")
        (ROOT / filename).write_text(page, encoding="utf-8")

    forbidden = ("squarespace", "typekit", "google fonts", "cdn.jsdelivr")
    generated_paths = (
        [ROOT / a.path for a in articles]
        + [ROOT / "blog-insights.html", ROOT / "blog.html", ROOT / PAGINATED_INDEX_ROUTE]
        + [ROOT / "insights" / "tag" / t for t in tag_registry]
        + [ROOT / f for f in LEGACY_TAG_ROUTES]
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
    print(f"Index pages rewritten: 3 (blog-insights.html, blog.html, mirrored offset list)")
    print(f"Legacy tag routes rewritten: {len(LEGACY_TAG_ROUTES)}")


if __name__ == "__main__":
    main()
