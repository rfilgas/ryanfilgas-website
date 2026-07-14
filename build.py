#!/usr/bin/env python3
"""Build the static site: galleries, text pages, and parent redirects.

Galleries are generated from the images in each page's ``assets/<folder>/``
directory, in filename order. Alt text is derived from the filename. Run:

    python3 build.py

The blog/Insights pages are generated separately by generate_insights.py.
"""
import re
from pathlib import Path

import components
import content

ROOT = Path(__file__).resolve().parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
DESCRIPTION = "Photographer and Digital Artist in Minneapolis, MN"


def alt_from_filename(path: Path) -> str:
    """Human-readable alt text from a numbered semantic filename.

    ponytail: naive filename->prose heuristic; if a photo needs richer alt
    text, rename the file or add an explicit override here.
    """
    stem = re.sub(r"^\d+[_-]", "", path.stem)          # drop NN_ order prefix
    words = re.sub(r"[_\-]+", " ", stem).strip()
    words = re.sub(r"\s+", " ", words)
    return words or path.stem


def gallery_photos(folder: str):
    directory = ROOT / "assets" / folder
    files = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        raise SystemExit(f"assets/{folder}/ has no images")
    return [(f"assets/{folder}/{p.name}", alt_from_filename(p)) for p in files]


def build_galleries():
    for slug, (title, label, folder, is_home) in content.GALLERIES.items():
        photos = gallery_photos(folder)
        body = components.gallery_main(label, photos)
        html = components.document(
            title=title,
            description=DESCRIPTION,
            body=body,
            active=f"{slug}.html",
            title_suffix=not is_home,
        )
        (ROOT / f"{slug}.html").write_text(html, encoding="utf-8")
        print(f"{slug}.html: {len(photos)} photos")


def build_text_pages():
    for slug, (title, description) in content.TEXT_PAGES.items():
        body = (ROOT / "content" / f"{slug}.html").read_text(encoding="utf-8").rstrip("\n")
        html = components.document(
            title=title,
            description=description,
            body="  " + body,
            active=f"{slug}.html",
        )
        (ROOT / f"{slug}.html").write_text(html, encoding="utf-8")
        print(f"{slug}.html: text page")


def build_redirects():
    for slug, target in content.REDIRECTS.items():
        html = (
            "<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "  <meta charset=\"utf-8\">\n"
            f"  <meta http-equiv=\"refresh\" content=\"0; url={target}\">\n"
            f"  <link rel=\"canonical\" href=\"{target}\">\n"
            "  <title>Ryan Filgas</title>\n</head>\n"
            f"<body><p><a href=\"{target}\">Continue to Ryan Filgas</a></p></body>\n</html>\n"
        )
        (ROOT / f"{slug}.html").write_text(html, encoding="utf-8")
        print(f"{slug}.html: redirect -> {target}")


def main():
    build_galleries()
    build_text_pages()
    build_redirects()
    print("build complete")


if __name__ == "__main__":
    main()
