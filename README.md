# ryanfilgas.com

A hand-maintained static site. No framework, no build dependencies — just Python 3
generating plain HTML from small, shared components. Open the generated `.html`
files directly or serve the folder with any static file server.

## Quick start

```bash
# Regenerate every page after changing content or assets:
python3 build.py              # galleries, text pages, redirects
python3 generate_insights.py  # blog listing, articles, tag pages

# Preview locally:
python3 -m http.server 8137
# then open http://localhost:8137/index.html
```

Both generators are idempotent — run them any time; they overwrite the generated
HTML in place.

## How it's organized

```
build.py                 # generates galleries, text pages, redirects
generate_insights.py     # generates the blog (listing + articles + tag pages)
components.py            # shared HTML: side menu, page shell, gallery markup (single source of truth)
content.py              # page registry — declare pages here
content/                # editable page bodies (about-*, connect, ...)
assets/
  site.css              # all styling
  gallery.js            # masonry layout + lightbox + mobile menu toggle
  logo.png              # header logo
  <slug>/               # one folder per gallery page, holds that page's ordered images
  content/              # figures for the about/connect pages
  blog/                 # blog post images (populated by generate_insights.py)
*.html, insights/**     # generated output — do not edit by hand
README.md
```

Everything you edit lives in `content.py`, `content/`, `components.py`, and the
`assets/` image folders. The `*.html` files are generated output.

## Images and naming

Each gallery page has its own folder under `assets/<slug>/`. Images are displayed
in **filename order**, so names are prefixed with a two-digit index and use a
semantic, human-readable name (the "semantic tag" is in the filename itself):

```
assets/landscape/01_forest_college_cove_trinidad_photo.jpg
assets/landscape/02_coastal_sunset.jpg
...
```

Alt text is derived automatically from the filename (index prefix stripped,
`_`/`-` turned into spaces), so a descriptive filename gives you descriptive,
accessible alt text for free.

## Common tasks

### Add photos to an existing gallery

1. Drop the image files into that page's folder, e.g. `assets/free-flight/`.
2. Name them with the next index prefix and a descriptive name:
   `30_sunrise_over_the_gorge.jpg`.
3. Run `python3 build.py`.

To reorder, just renumber the filename prefixes.

### Add a new gallery page

1. Create `assets/<slug>/` and add your numbered, named images.
2. Register the page in `content.py` under `GALLERIES`:
   ```python
   "my-gallery": ("Short Title", "Gallery Heading", "my-gallery", False),
   #  output slug   nav/title       aria-label / on-page heading   folder   is_home
   ```
3. Add it to the side menu in `components.py` — put a `("Label", "my-gallery.html")`
   tuple in `ART_CHILDREN` or `WORK_CHILDREN` (or `MAIN_LINKS` for a top-level item).
4. Run `python3 build.py`.

### Add a text page (like About / Connect)

1. Create `content/<slug>.html` containing a `<main class="content-page">…</main>`
   body (copy an existing one in `content/` as a starting point).
2. Register it in `content.py` under `TEXT_PAGES`:
   ```python
   "<slug>": ("Page Title", "Meta description for search engines"),
   ```
3. Add it to the side menu in `components.py` (`MAIN_LINKS`).
4. Run `python3 build.py`.

### Add a redirect

Add an entry to `REDIRECTS` in `content.py` (`"old-url": "target.html"`) and run
`python3 build.py`.

### Add a blog post

Blog articles are sourced from the archived content in the `generate_insights.py`
registry (`ARTICLE_PATHS`). To add a new post, add its body to that pipeline and
run `python3 generate_insights.py`. Post images are copied into `assets/blog/`
automatically.

## The side menu

The fixed left side menu is defined once in `components.py` (`ART_CHILDREN`,
`WORK_CHILDREN`, `MAIN_LINKS`, `SOCIAL_LINKS`) and rendered on every page. On
screens narrower than 700px it collapses behind a "Menu" button; the toggle logic
lives in `assets/gallery.js`. Edit the menu in one place and rerun the generators.

## Tests

Functional tests use Playwright. See `tests/` for the suite:

```bash
python3 -m http.server 8137     # serve the site
npx playwright test             # run the functional tests (multiple viewports)
```
