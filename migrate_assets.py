#!/usr/bin/env python3
"""One-time migration: build per-page gallery asset folders from the original
Squarespace mirror (git commit b20f73c). After this runs, ``assets/<slug>/`` is
the source of truth for galleries -- add photos by dropping numbered files in and
rerunning build.py. This script is kept only for provenance/reproducibility.

ponytail: reads the mirror once; not part of the normal build.
"""
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote
from html.parser import HTMLParser

MIRROR_COMMIT = "b20f73c"

# source mirror page slug -> output gallery folder under assets/
GALLERIES = {
    "index": "narrative-portraiture",
    "landscape": "landscape",
    "arial-silks": "arial-silks",
    "free-flight": "free-flight",
    "digital-art": "digital-art",
    "editorial-happy-hour": "editorial-happy-hour",
    "architecture-interior": "architecture-interior",
    "architecture-exterior": "architecture-exterior",
}

HASH = "-9ee94cce"


def build_local_index():
    """Map every candidate stem spelling -> local file path."""
    index = {}
    for root in ("assets/gallery", "assets/photos"):
        for path in Path(root).rglob("*"):
            if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            stem = path.stem
            if stem.endswith(HASH):
                stem = stem[: -len(HASH)]
            for key in {stem, unquote(stem), stem.replace("+", " ")}:
                index.setdefault(key, path)
    return index


class GalleryImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.srcs = []

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        data = dict(attrs)
        src = data.get("src") or data.get("data-src") or ""
        if "images.squarespace-cdn" in src:
            self.srcs.append(src)


def ordered_images(slug):
    html = subprocess.check_output(
        ["git", "show", f"{MIRROR_COMMIT}:{slug}.html"], text=True
    )
    parser = GalleryImages()
    parser.feed(html)
    seen, names = set(), []
    for src in parser.srcs:
        base = src.split("/")[-1].split("?")[0]
        base = re.sub(r"\.(jpg|jpeg|png)$", "", base, flags=re.I)
        if "RF-logo" in base:  # header logo, not a gallery photo
            continue
        if base in seen:
            continue
        seen.add(base)
        names.append(base)
    return names


def clean_name(raw):
    """URL-decode and normalise a filename to a readable slug (no extension)."""
    name = unquote(raw)
    name = name.replace("+", "-").replace(" ", "-").replace("(", "").replace(")", "")
    name = re.sub(r"-+", "-", name).strip("-_")
    return name


def resolve(raw, local):
    for key in (raw, unquote(raw), raw.replace("+", " "), unquote(raw).replace("+", " ")):
        if key in local:
            return local[key]
    return None


def main():
    local = build_local_index()
    missing = []
    for slug, folder in GALLERIES.items():
        dest_dir = Path("assets") / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        names = ordered_images(slug)
        for i, raw in enumerate(names, 1):
            source = resolve(raw, local)
            if source is None:
                missing.append((slug, raw))
                continue
            ext = source.suffix.lower()
            dest = dest_dir / f"{i:02d}_{clean_name(raw)}{ext}"
            shutil.copy2(source, dest)
        print(f"{folder}: {len(names)} images")
    if missing:
        raise SystemExit(f"UNRESOLVED IMAGES: {missing}")
    print("migration complete")


if __name__ == "__main__":
    main()
