#!/usr/bin/env python3
"""Shared HTML components for the site. Both build.py (galleries + text pages)
and generate_insights.py (blog) render through these functions so the shell,
side menu, and footer stay identical across every page.

``prefix`` is the relative path back to the site root (e.g. "" for top-level
pages, "../../../../" for a blog article under insights/YYYY/M/D/). Every asset
and nav href is prefixed with it, so the same nav works at any depth.
"""
from html import escape

# ── Navigation: single source of truth for the side menu ──────────────
# Parent labels ("Art", "Work") are themselves links (Art -> home, Work ->
# Happy Hour) on the live site, and expand to their children.
ART_CHILDREN = [
    ("Narrative Portraiture", "index.html"),
    ("Landscape", "landscape.html"),
    ("Aerial Silks", "arial-silks.html"),
    ("Free Flight", "free-flight.html"),
    ("Digital Art", "digital-art.html"),
]
WORK_CHILDREN = [
    ("Happy Hour", "editorial-happy-hour.html"),
    ("Arch-Interiors", "architecture-interior.html"),
    ("Arch-Exteriors", "architecture-exterior.html"),
]
MAIN_LINKS = [
    ("About Me (Art)", "about-me-art.html"),
    ("About Me (SWE)", "about-software-engineering.html"),
    ("Connect", "connect.html"),
    ("Insights", "blog-insights.html"),
]
SOCIAL_LINKS = [
    ("Email", "mailto:ryan@ryanfilgas.com"),
    ("LinkedIn", "https://www.linkedin.com/pub/ryan-filgas/7a/650/725"),
    ("GitHub", "https://github.com/rfilgas"),
]


def _href(target, prefix):
    if target.startswith(("http:", "https:", "mailto:", "#")):
        return target
    return prefix + target


def _link(label, target, active, prefix):
    current = ' aria-current="page"' if target == active else ""
    return f'<a href="{_href(target, prefix)}"{current}>{escape(label)}</a>'


def _submenu(label, parent_target, children, active, prefix):
    parent_current = active == parent_target or any(active == t for _, t in children)
    summary_current = ' aria-current="page"' if parent_current else ""
    items = "".join(
        f"<li>{_link(text, target, active, prefix)}</li>" for text, target in children
    )
    parent = _link(label, parent_target, active, prefix)
    return (
        f"<li><details open><summary{summary_current}>{parent}</summary>"
        f"<ul>{items}</ul></details></li>"
    )


def header(active="", prefix=""):
    """Site header + fixed side menu, identical on every page."""
    art = _submenu("Art", "index.html", ART_CHILDREN, active, prefix)
    work = _submenu("Work", "editorial-happy-hour.html", WORK_CHILDREN, active, prefix)
    main = "".join(f"<li>{_link(t, h, active, prefix)}</li>" for t, h in MAIN_LINKS)
    social = "".join(
        f'<a href="{_href(h, prefix)}">{escape(t)}</a>' for t, h in SOCIAL_LINKS
    )
    return f"""  <header class="site-header">
    <a class="logo" href="{prefix}index.html" aria-label="Ryan Filgas home"><img src="{prefix}assets/logo.png" alt="RYAN FILGAS"></a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-navigation">Menu</button>
    <nav class="site-nav" id="site-navigation" aria-label="Main navigation">
      <ul>
        {art}
        {work}
        {main}
      </ul>
    </nav>
    <footer class="site-footer">{social}</footer>
  </header>"""


def document(*, title, description, body, active="", prefix="", title_suffix=True):
    """Wrap page ``body`` (everything inside <body> after the header) in the
    full HTML shell. ``body`` should be the <main>/<section> markup."""
    full_title = f"{escape(title)} | Ryan Filgas" if title_suffix else escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(description, quote=True)}">
  <title>{full_title}</title>
  <link rel="stylesheet" href="{prefix}assets/site.css">
  <script src="{prefix}assets/gallery.js" defer></script>
</head>
<body>
{header(active, prefix)}
{body}
</body>
</html>
"""


def gallery_main(label, photos):
    """Gallery grid + lightbox viewer. ``photos`` is a list of (src, alt)."""
    cards = []
    for i, (src, alt) in enumerate(photos):
        loading = "" if i == 0 else ' loading="lazy"'
        cards.append(
            f'      <button class="photo" type="button">'
            f'<img src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}"{loading}></button>'
        )
    grid = "\n".join(cards)
    return f"""  <main class="gallery" aria-label="{escape(label, quote=True)}">
    <div class="gallery-columns">
{grid}
    </div>
  </main>
  <section class="viewer" aria-label="Selected photo" aria-live="polite">
    <div class="viewer-controls"><button type="button" data-action="previous">Previous</button><button type="button" data-action="thumbnails">Show Thumbnails</button><button type="button" data-action="next">Next</button></div>
    <div class="viewer-image"><img alt=""></div>
    <div class="viewer-numbers" aria-label="Photo navigation"></div>
  </section>"""
