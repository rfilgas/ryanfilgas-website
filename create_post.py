#!/usr/bin/env python3
"""Create and publish Insights posts from a simple Markdown source file.

Authoring format:
- YAML-like frontmatter between --- lines
- Required: title
- Optional: date (YYYY-MM-DD), tags (comma separated or [list]), slug
- Body: plain paragraphs, headings (#/##/###), and inline image lines:
  ![alt text](assets/blog/example.jpg)

Publish flow:
1) Compile Markdown source into insights/YYYY/M/D/slug.html
2) Rebuild Insights index/tag pages by running generate_insights.py
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import components

ROOT = Path(__file__).resolve().parent
ALLOWED_REMOTE_PREFIXES = (
    "https://www.youtube.com/",
    "https://youtube.com/",
    "https://www.linkedin.com/",
    "https://linkedin.com/",
    "https://github.com/",
    "mailto:",
)
FORBIDDEN_TERMS = ("typekit", "google fonts", "cdn.jsdelivr")
PUBLISH_MAP_PATH = ROOT / "content" / "posts" / ".publish-map.json"


@dataclass
class PostSource:
    source_path: Path
    title: str
    date_value: date
    tags: list[str]
    slug: str
    body_markdown: str


class PostError(ValueError):
    """Raised for user-facing publish errors."""


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered or "post"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines(keepends=True)
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise PostError("Frontmatter opens with --- but no closing --- was found")

    frontmatter_lines = lines[1:end_idx]
    body = "".join(lines[end_idx + 1 :])
    parsed: dict[str, str] = {}
    for raw in frontmatter_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise PostError(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        parsed[key.strip().lower()] = value.strip()
    return parsed, body


def parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    tags = [part.strip().strip('"').strip("'") for part in cleaned.split(",")]
    tags = [tag for tag in tags if tag]
    return tags


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise PostError("date must be YYYY-MM-DD") from exc


def parse_post_source(path: Path) -> PostSource:
    if not path.is_file():
        raise PostError(f"Source file not found: {path}")

    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    title = fm.get("title", "").strip()
    if not title:
        raise PostError("Frontmatter requires a title")

    body_markdown = body.strip()
    if not body_markdown:
        raise PostError("Post body is empty")

    post_date = parse_date(fm.get("date"))
    tags = parse_tags(fm.get("tags"))
    slug_value = fm.get("slug", "").strip()
    slug = slugify(slug_value or title)

    return PostSource(
        source_path=path,
        title=title,
        date_value=post_date,
        tags=tags,
        slug=slug,
        body_markdown=body_markdown,
    )


def relpath_to_root(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def article_dir_for_date(day: date) -> str:
    return f"insights/{day.year}/{day.month}/{day.day}"


def display_date(day: date) -> str:
    return day.strftime("%B %d, %Y").replace(" 0", " ")


def resolve_image_source(raw: str, source_file: Path) -> tuple[Path, str]:
    candidate = source_file.parent / raw
    if candidate.is_file():
        abs_path = candidate.resolve()
    else:
        root_candidate = ROOT / raw
        if root_candidate.is_file():
            abs_path = root_candidate.resolve()
        else:
            raise PostError(f"Image not found for markdown image: {raw}")

    if ROOT not in abs_path.parents and abs_path != ROOT:
        raise PostError(f"Image must be inside repository root: {raw}")

    rel_root = relpath_to_root(abs_path)
    return abs_path, rel_root


def convert_inline_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        href = match.group(2).strip()
        if not href:
            return escape(match.group(0))
        return f'<a href="{escape(href, quote=True)}">{escape(label)}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, escape(text))


def markdown_to_html(markdown: str, source_file: Path, article_dir: str) -> str:
    html_parts: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        joined = " ".join(line.strip() for line in paragraph if line.strip())
        if joined:
            html_parts.append(f"<p>{convert_inline_links(joined)}</p>")
        paragraph.clear()

    def flush_list() -> None:
        if not list_items:
            return
        items = "".join(f"<li>{convert_inline_links(item)}</li>" for item in list_items)
        html_parts.append(f"<ul>{items}</ul>")
        list_items.clear()

    image_pattern = re.compile(r"^!\[(.*?)\]\(([^)]+)\)\s*$")
    heading_pattern = re.compile(r"^(#{1,3})\s+(.*)$")

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        image_match = image_pattern.match(line.strip())
        if image_match:
            flush_paragraph()
            flush_list()
            alt = image_match.group(1).strip()
            src_raw = image_match.group(2).strip()
            parsed = urlparse(src_raw)
            if parsed.scheme or parsed.netloc:
                raise PostError(f"Remote image URLs are not allowed: {src_raw}")
            _, rel_root = resolve_image_source(src_raw, source_file)
            image_src = posixpath.relpath(rel_root, article_dir)
            html_parts.append(
                "<figure class=\"post-figure\">"
                f"<img src=\"{escape(image_src, quote=True)}\" alt=\"{escape(alt, quote=True)}\" loading=\"lazy\">"
                "</figure>"
            )
            continue

        heading_match = heading_pattern.match(line)
        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            tag = {1: "h2", 2: "h3", 3: "h4"}[level]
            html_parts.append(f"<{tag}>{escape(heading_match.group(2).strip())}</{tag}>")
            continue

        list_match = re.match(r"^\s*-\s+(.*)$", line)
        if list_match:
            flush_paragraph()
            list_items.append(list_match.group(1).strip())
            continue

        flush_list()

        paragraph.append(line)

    flush_paragraph()
    flush_list()

    if not html_parts:
        raise PostError("No renderable content found in post body")

    return "\n    ".join(html_parts)


def tag_filename(tag_name: str) -> str:
    return f"{slugify(tag_name)}.html"


def render_tags_line(tags: list[str], article_dir: str) -> str:
    if not tags:
        return ""
    links = []
    for tag in tags:
        target = f"insights/tag/{tag_filename(tag)}"
        href = posixpath.relpath(target, article_dir)
        links.append(f'<a href="{escape(href, quote=True)}">{escape(tag)}</a>')
    return f'    <p class="post-tags">Tags: {", ".join(links)}</p>\n'


def source_marker_value(source_path: Path) -> str:
    return relpath_to_root(source_path)


def load_publish_map() -> dict[str, str]:
    if not PUBLISH_MAP_PATH.is_file():
        return {}
    try:
        parsed = json.loads(PUBLISH_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PostError(f"Invalid publish map JSON: {PUBLISH_MAP_PATH}") from exc
    if not isinstance(parsed, dict):
        raise PostError(f"Invalid publish map format: {PUBLISH_MAP_PATH}")
    return {str(k): str(v) for k, v in parsed.items()}


def save_publish_map(mapping: dict[str, str]) -> None:
    PUBLISH_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLISH_MAP_PATH.write_text(
        json.dumps(mapping, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def extract_h1_title(html_text: str) -> str | None:
    match = re.search(r"<h1>(.*?)</h1>", html_text, re.S)
    if not match:
        return None
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def choose_article_output_path(post: PostSource, publish_map: dict[str, str]) -> Path:
    base_dir = ROOT / article_dir_for_date(post.date_value)
    base_dir.mkdir(parents=True, exist_ok=True)

    source_key = source_marker_value(post.source_path)
    mapped_rel = publish_map.get(source_key)
    if mapped_rel:
        mapped_abs = ROOT / mapped_rel
        if mapped_abs.is_file():
            return mapped_abs

    reserved_outputs = {v for k, v in publish_map.items() if k != source_key}

    attempt = 1
    while True:
        suffix = "" if attempt == 1 else f"-{attempt}"
        filename = f"{post.slug}{suffix}.html"
        candidate = base_dir / filename
        candidate_rel = relpath_to_root(candidate)

        if not candidate.exists() and candidate_rel not in reserved_outputs:
            return candidate

        if candidate.exists() and candidate_rel not in reserved_outputs:
            existing_title = extract_h1_title(candidate.read_text(encoding="utf-8"))
            if existing_title == post.title:
                return candidate

        attempt += 1


def render_article_html(post: PostSource, output_path: Path) -> str:
    article_rel = relpath_to_root(output_path)
    article_dir = posixpath.dirname(article_rel)
    body_html = markdown_to_html(post.body_markdown, post.source_path, article_dir)
    tags_line = render_tags_line(post.tags, article_dir)

    main = (
        "  <!-- source-post: "
        + escape(source_marker_value(post.source_path))
        + " -->\n"
        + "  <main class=\"content-page post\">\n"
        + f"    <p class=\"post-meta\"><time datetime=\"{post.date_value.isoformat()}\">{escape(display_date(post.date_value))}</time></p>\n"
        + f"    <h1>{escape(post.title)}</h1>\n"
        + tags_line
        + f"    {body_html}\n"
        + "  </main>"
    )

    prefix = posixpath.relpath(".", article_dir) + "/"
    return components.document(
        title=post.title,
        description=f"{post.title} - Insights by Ryan Filgas",
        body=main,
        active="insights/",
        prefix=prefix,
    )


def validate_generated_html(html_text: str) -> None:
    lowered = html_text.lower()

    for token in ("http://", "https://"):
        for match in re.finditer(re.escape(token) + r"[^\"'\s<>]+", lowered):
            url = match.group(0)
            if any(url.startswith(prefix) for prefix in ALLOWED_REMOTE_PREFIXES):
                continue
            raise PostError(f"unexpected remote reference: {url}")

    for forbidden in FORBIDDEN_TERMS:
        if forbidden in lowered:
            raise PostError(f"forbidden external reference: {forbidden}")


def publish(source: Path) -> int:
    post = parse_post_source(source)
    publish_map = load_publish_map()
    output_path = choose_article_output_path(post, publish_map)
    html_text = render_article_html(post, output_path)
    validate_generated_html(html_text)

    output_path.write_text(html_text, encoding="utf-8")
    rel_output = relpath_to_root(output_path)
    publish_map[source_marker_value(post.source_path)] = rel_output
    save_publish_map(publish_map)
    print(f"Wrote article: {rel_output}")

    cmd = [sys.executable, str(ROOT / "generate_insights.py")]
    subprocess.run(cmd, check=True, cwd=ROOT)
    print("Regenerated insights index/tag pages")
    return 0


def normalize_repo_relative(path: Path) -> str:
    if path.is_absolute():
        return relpath_to_root(path)
    return path.as_posix()


def unpublish(target: str) -> int:
    publish_map = load_publish_map()
    target_path = Path(target)
    target_rel = normalize_repo_relative(target_path)

    remove_keys: list[str] = []
    rel_output: str | None = None

    if target_rel in publish_map:
        remove_keys.append(target_rel)
        rel_output = publish_map[target_rel]
    else:
        mapped_sources = [source for source, output in publish_map.items() if output == target_rel]
        if mapped_sources:
            remove_keys.extend(mapped_sources)
            rel_output = target_rel

    if rel_output is None and target_rel.startswith("insights/") and target_rel.endswith(".html"):
        rel_output = target_rel

    if rel_output is None:
        raise PostError(
            "Target not found. Provide a source path from content/posts/ or an insights HTML path"
        )

    output_path = ROOT / rel_output
    deleted_output = False
    if output_path.is_file():
        output_path.unlink()
        deleted_output = True

    for key in remove_keys:
        publish_map.pop(key, None)
    save_publish_map(publish_map)

    if not deleted_output and not remove_keys:
        raise PostError(f"No mapped source or article file found for: {target}")

    if deleted_output:
        print(f"Removed article: {rel_output}")
    if remove_keys:
        print(f"Removed publish map entries: {', '.join(remove_keys)}")

    cmd = [sys.executable, str(ROOT / "generate_insights.py")]
    subprocess.run(cmd, check=True, cwd=ROOT)
    print("Regenerated insights index/tag pages")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and publish an Insights post from a Markdown source file"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish_parser = subparsers.add_parser("publish", help="Publish a source post")
    publish_parser.add_argument(
        "source",
        help="Path to source markdown file (example: content/posts/my-post.md)",
    )

    unpublish_parser = subparsers.add_parser("unpublish", help="Remove a published post")
    unpublish_parser.add_argument(
        "target",
        help=(
            "Source markdown path (content/posts/my-post.md) or published article path "
            "(insights/YYYY/M/D/my-post.html)"
        ),
    )

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.command == "publish":
        source_path = Path(args.source)
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        return publish(source_path)

    if args.command == "unpublish":
        return unpublish(args.target)

    raise PostError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except PostError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
