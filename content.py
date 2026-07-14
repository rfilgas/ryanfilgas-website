#!/usr/bin/env python3
"""Page registry: the single place to declare pages.

To add a gallery page: drop numbered images in ``assets/<folder>/`` and add an
entry to GALLERIES. To add a text page: add an entry to TEXT_PAGES and create
``content/<slug>.html`` with a ``<main class="content-page">`` body.
See README.md for full steps.
"""

# output_slug -> (short title, gallery aria-label, asset folder, is_home)
GALLERIES = {
    "index": ("Ryan Filgas", "Narrative Portraiture", "narrative-portraiture", True),
    "landscape": ("Landscape", "Landscape", "landscape", False),
    "arial-silks": ("Aerial Silks", "Aerial Silks", "arial-silks", False),
    "free-flight": ("Free Flight", "Free Flight", "free-flight", False),
    "digital-art": ("Digital Art", "Digital Art", "digital-art", False),
    "editorial-happy-hour": ("Happy Hour", "Editorial - Happy Hour", "editorial-happy-hour", False),
    "architecture-interior": ("Architecture Interiors", "Architecture Interiors", "architecture-interior", False),
    "architecture-exterior": ("Architecture Exteriors", "Architecture Exteriors", "architecture-exterior", False),
}

# output_slug -> (title, description). Body comes from content/<slug>.html
TEXT_PAGES = {
    "about-me-art": ("About Me (Art)", "About Ryan Filgas \u2013 photographer and digital artist in Minneapolis, MN"),
    "about-software-engineering": ("About Me (SWE)", "Ryan Filgas \u2013 software engineer"),
    "connect": ("Connect", "Get in touch with Ryan Filgas"),
}

# redirect page -> target (parent nav links on the live site)
REDIRECTS = {
    "art": "index.html",
    "work": "editorial-happy-hour.html",
}
