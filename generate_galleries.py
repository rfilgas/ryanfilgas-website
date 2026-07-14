#!/usr/bin/env python3
"""Build the native gallery pages from their local mirrored images."""

from html import escape
from html.parser import HTMLParser
from pathlib import Path
import shutil


PAGES = {
    "art": ("Narrative Portraiture", "Narrative Portraiture"),
    "landscape": ("Landscape", "Landscape"),
    "arial-silks": ("Aerial Silks", "Aerial Silks"),
    "free-flight": ("Free Flight", "Free Flight"),
    "digital-art": ("Digital Art", "Digital Art"),
    "work": ("Editorial - Happy Hour", "Happy Hour"),
    "editorial-happy-hour": ("Editorial Happy Hour", "Happy Hour"),
    "architecture-exterior": ("Architecture Exteriors", "Arch-Exteriors"),
    "architecture-interior": ("Architecture Interiors", "Arch-Interiors"),
}


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img":
            classes = attributes.get("class", "").split()
            in_photo = any("photo" in item[1].get("class", "").split() for item in self.stack)
            self.images.append((attributes, "load-false" in classes, in_photo))
        self.stack.append((tag, attributes))

    def handle_startendtag(self, tag, attrs):
        if tag == "img":
            self.images.append((dict(attrs), "load-false" in dict(attrs).get("class", "").split(), False))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def extract_images(page):
    parser = ImageParser()
    parser.feed(page.read_text(encoding="utf-8"))
    legacy = [attributes for attributes, is_legacy, _ in parser.images if is_legacy]
    native = [attributes for attributes, _, in_photo in parser.images if in_photo]
    images = legacy or native
    if not images:
        raise ValueError(f"{page}: no gallery images found")
    return [(image["src"], image.get("alt", "")) for image in images]


def local_gallery_path(source):
    if source.startswith("assets/images.squarespace-cdn.com/"):
        original = Path(source)
        if not original.is_file():
            raise FileNotFoundError(original)
        destination = Path("assets/gallery") / original.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(original, destination)
        return destination.as_posix()
    if source.startswith(("http:", "https:", "//")):
        raise ValueError(f"remote gallery image: {source}")
    if not Path(source).is_file():
        raise FileNotFoundError(source)
    return source


def nav_link(label, href, current):
    attribute = ' aria-current="page"' if current else ""
    return f'<a href="{href}"{attribute}>{label}</a>'


def header(current):
    art_current = current == "art"
    work_current = current in {"work", "editorial-happy-hour"}
    art_links = [
        nav_link("Narrative Portraiture", "index.html", False),
        nav_link("Landscape", "landscape.html", current == "landscape"),
        nav_link("Aerial Silks", "arial-silks.html", current == "arial-silks"),
        nav_link("Free Flight", "free-flight.html", current == "free-flight"),
        nav_link("Digital Art", "digital-art.html", current == "digital-art"),
    ]
    work_links = [
        nav_link("Happy Hour", "editorial-happy-hour.html", current in {"work", "editorial-happy-hour"}),
        nav_link("Arch-Interiors", "architecture-interior.html", current == "architecture-interior"),
        nav_link("Arch-Exteriors", "architecture-exterior.html", current == "architecture-exterior"),
    ]
    art_summary = ' aria-current="page"' if art_current else ""
    work_summary = ' aria-current="page"' if work_current else ""
    return f"""  <header class="site-header">
    <a class="logo" href="index.html" aria-label="Ryan Filgas home"><img src="assets/photos/01.jpg" alt="Ryan Filgas"></a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-navigation">Menu</button>
    <nav class="site-nav" id="site-navigation" aria-label="Main navigation">
      <ul>
        <li><details open><summary{art_summary}>Art</summary><ul><li>{'</li><li>'.join(art_links)}</li></ul></details></li>
        <li><details open><summary{work_summary}>Work</summary><ul><li>{'</li><li>'.join(work_links)}</li></ul></details></li>
        <li>{nav_link("About Me (Art)", "about-me-art.html", False)}</li>
        <li>{nav_link("About Me (SWE)", "about-software-engineering.html", False)}</li>
        <li>{nav_link("Connect", "connect.html", False)}</li>
        <li>{nav_link("Insights", "blog-insights.html", False)}</li>
      </ul>
    </nav>
    <footer class="site-footer"><a href="mailto:ryan@ryanfilgas.com">Email</a></footer>
  </header>"""


def render(slug, title, label, images):
    photo_markup = []
    for index, (source, alt) in enumerate(images):
        loading = "" if index == 0 else ' loading="lazy"'
        photo_markup.append(
            f'      <button class="photo" type="button"><img src="{escape(source, quote=True)}"'
            f' alt="{escape(alt, quote=True)}"{loading}></button>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Photographer and Digital Artist in Minneapolis, MN">
  <title>{escape(title)} | Ryan Filgas</title>
  <link rel="stylesheet" href="assets/native.css">
  <script src="assets/native-gallery.js" defer></script>
</head>
<body>
{header(slug)}
  <main class="gallery" aria-label="{escape(label, quote=True)}">
    <div class="gallery-columns">
{chr(10).join(photo_markup)}
    </div>
  </main>
  <section class="viewer" aria-label="Selected photo" aria-live="polite">
    <div class="viewer-controls"><button type="button" data-action="previous">Previous</button><button type="button" data-action="thumbnails">Show Thumbnails</button><button type="button" data-action="next">Next</button></div>
    <div class="viewer-image"><img alt=""></div>
    <div class="viewer-numbers" aria-label="Photo navigation"></div>
  </section>
</body>
</html>
"""


def main():
    for slug, (title, label) in PAGES.items():
        page = Path(f"{slug}.html")
        source_images = extract_images(page)
        images = [(local_gallery_path(source), alt) for source, alt in source_images]
        output = render(slug, title, label, images)
        generated = ImageParser()
        generated.feed(output)
        generated_images = [attributes for attributes, _, in_photo in generated.images if in_photo]
        if len(generated_images) != len(images):
            raise ValueError(f"{page}: source has {len(images)} images but output has {len(generated_images)}")
        forbidden = ("http", "squarespace", "typekit", "google fonts")
        if any(value in output.lower() for value in forbidden):
            raise ValueError(f"{page}: generated output contains a forbidden remote reference")
        page.write_text(output, encoding="utf-8")
        print(f"{page}: {len(source_images)} source images -> {len(generated_images)} generated images")


if __name__ == "__main__":
    main()
