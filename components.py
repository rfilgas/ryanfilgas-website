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
# Parent labels ("Art", "Work") are links to redirect routes (`art/`,
# `work/`) and expand to their children.
ART_CHILDREN = [
    ("Narrative Portraiture", "index.html"),
    ("Landscape", "landscape/"),
    ("Aerial Silks", "arial-silks/"),
    ("Free Flight", "free-flight/"),
    ("Digital Art", "digital-art/"),
]
WORK_CHILDREN = [
    ("Happy Hour", "editorial-happy-hour/"),
    ("Arch-Interiors", "architecture-interior/"),
    ("Arch-Exteriors", "architecture-exterior/"),
]
MAIN_LINKS = [
    ("About Me (Art)", "about-me-art/"),
    ("About Me (SWE)", "about-software-engineering/"),
    ("Connect", "connect/"),
    ("Insights", "insights/"),
]
SOCIAL_LINKS = [
    ("Email", "mailto:ryan@ryanfilgas.com", "email"),
    ("LinkedIn", "https://www.linkedin.com/pub/ryan-filgas/7a/650/725", "linkedin"),
    ("GitHub", "https://github.com/rfilgas", "github"),
]


def _href(target, prefix):
    if target.startswith(("http:", "https:", "mailto:", "#")):
        return target
    return prefix + target


def _link(label, target, active, prefix):
    current = ' aria-current="page"' if target == active else ""
    return f'<a href="{_href(target, prefix)}"{current}>{escape(label)}</a>'


def _submenu(label, parent_target, children, active, prefix):
    is_open = active == parent_target or any(target == active for _, target in children)
    open_attr = " open" if is_open else ""
    items = "".join(
        f"<li>{_link(text, target, active, prefix)}</li>" for text, target in children
    )
    parent = _link(label, parent_target, active, prefix)
    return (
        f"<li><details{open_attr}><summary>{parent}</summary>"
        f"<ul>{items}</ul></details></li>"
    )


def _social_icon(kind):
    if kind == "email":
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M3 6h18v12H3z" fill="none" stroke="currentColor" stroke-width="1.8"/>'
            '<path d="m4 7 8 6 8-6" fill="none" stroke="currentColor" stroke-width="1.8"/>'
            "</svg>"
        )
    if kind == "linkedin":
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M4 9h4v11H4zM6 4.2a2.3 2.3 0 1 1 0 4.6 2.3 2.3 0 0 1 0-4.6Zm5 4.8h3.8v1.6h.1a4.1 4.1 0 0 1 3.7-2c3.9 0 4.6 2.5 4.6 5.9V20h-4v-4.9c0-1.2 0-2.8-1.8-2.8s-2 1.3-2 2.7V20h-4z" fill="currentColor"/>'
            "</svg>"
        )
    return (
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-2c-3 .7-3.6-1.2-3.6-1.2-.5-1.2-1.2-1.6-1.2-1.6-1-.6.1-.6.1-.6 1 .1 1.6 1.1 1.6 1.1 1 .1 1.8 1.4 2.6 1.8.1-.7.4-1.2.7-1.5-2.4-.3-4.9-1.2-4.9-5.4 0-1.2.4-2.2 1.1-3-.1-.3-.5-1.4.1-2.9 0 0 .9-.3 3 .9a10.3 10.3 0 0 1 5.5 0c2.1-1.2 3-.9 3-.9.6 1.5.2 2.6.1 2.9.7.8 1.1 1.8 1.1 3 0 4.2-2.5 5.1-5 5.4.4.3.8 1 .8 2.1v3.1c0 .3.2.7.8.5A10 10 0 0 0 12 2Z" fill="currentColor"/>'
        "</svg>"
    )


def header(active="", prefix=""):
    """Site header + fixed side menu, identical on every page."""
    art = _submenu("Art", "art/", ART_CHILDREN, active, prefix)
    work = _submenu("Work", "work/", WORK_CHILDREN, active, prefix)
    main = "".join(f"<li>{_link(t, h, active, prefix)}</li>" for t, h in MAIN_LINKS)
    social = "".join(
        f'<a class="social-link" href="{_href(h, prefix)}" aria-label="{escape(t, quote=True)}"><span class="sr-only">{escape(t)}</span>{_social_icon(icon)}</a>'
        for t, h, icon in SOCIAL_LINKS
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
  <link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{prefix}assets/site.css">
  <script src="{prefix}assets/gallery.js" defer></script>
</head>
<body>
{header(active, prefix)}
{body}
  <div class="site-copyright">© RYAN FILGAS. ALL RIGHTS RESERVED</div>
</body>
</html>
"""


def gallery_main(label, photos, prefix=""):
    """Gallery grid + in-flow selected photo view. ``photos`` is a list of (src, alt)."""
    cards = []
    for i, (src, alt) in enumerate(photos):
        loading = "" if i == 0 else ' loading="lazy"'
        cards.append(
            f'      <button class="photo" type="button" data-photo="{i + 1}">'
            f'<img src="{prefix}{escape(src, quote=True)}" alt="{escape(alt, quote=True)}"{loading}></button>'
        )
    grid = "\n".join(cards)
    return f"""  <main class="gallery" aria-label="{escape(label, quote=True)}">
    <section class="gallery-selected" aria-label="Selected photo" hidden>
      <figure class="gallery-selected-image"><img alt=""></figure>
      <div class="gallery-selected-meta">
        <div class="gallery-selected-numbers" aria-label="Photo navigation"></div>
        <button class="gallery-thumbnails-toggle" type="button" data-action="thumbnails">show thumbnails</button>
      </div>
    </section>
    <div class="gallery-columns">
{grid}
    </div>
  </main>"""
