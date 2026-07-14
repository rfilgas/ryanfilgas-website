const { test, expect } = require('@playwright/test');

const pagesFromNav = [
  'index.html',
  'landscape/',
  'arial-silks/',
  'free-flight/',
  'digital-art/',
  'editorial-happy-hour/',
  'architecture-interior/',
  'architecture-exterior/',
  'about-me-art/',
  'about-software-engineering/',
  'connect/',
  'insights/',
];

test('side menu matches desktop and mobile behavior', async ({ page }, testInfo) => {
  await page.goto('/index.html');
  const nav = page.locator('nav.site-nav');
  const toggle = page.locator('button.menu-toggle');

  if (testInfo.project.name === 'mobile') {
    await expect(nav).toBeHidden();
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await toggle.click();
    await expect(nav).toHaveClass(/is-open/);
    await expect(nav).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  } else {
    await expect(nav).toBeVisible();
    await expect(toggle).toBeHidden();
  }
});

test('art and work parents are disclosure controls only', async ({ page }) => {
  await page.goto('/connect/');
  await expect(page.locator('summary', { hasText: 'Art' })).toBeVisible();
  await expect(page.locator('summary', { hasText: 'Work' })).toBeVisible();
  await expect(page.locator('summary a', { hasText: 'Art' })).toHaveCount(0);
  await expect(page.locator('summary a', { hasText: 'Work' })).toHaveCount(0);

  const artDetails = page.locator('nav.site-nav details').first();
  await expect(artDetails).not.toHaveAttribute('open', '');
  await page.locator('summary', { hasText: 'Art' }).click();
  await expect(artDetails).toHaveAttribute('open', '');
});

test('index side menu links reach expected site pages', async ({ page, request }) => {
  await page.goto('/index.html');
  const navHrefs = await page.locator('nav.site-nav a').evaluateAll((links) =>
    links.map((link) => link.getAttribute('href'))
  );

  for (const target of pagesFromNav) {
    expect(navHrefs).toContain(target);
    const response = await request.get(`/${target}`);
    expect(response.status(), `${target} should return HTTP 200`).toBe(200);
  }
});

test('gallery selected photo stays in flow with number controls and thumbnail toggle', async ({ page }) => {
  await page.goto('/index.html');

  const firstPhoto = page.locator('.gallery-columns .photo').first();
  const galleryColumns = page.locator('.gallery-columns');
  const selectedPanel = page.locator('.gallery-selected');
  const selectedImage = page.locator('.gallery-selected-image img');
  const numbers = page.locator('.gallery-selected-numbers button');
  const nextZone = page.locator('.gallery-selected-nav-zone-next');
  const previousZone = page.locator('.gallery-selected-nav-zone-prev');
  const showThumbnails = page.locator('.gallery-thumbnails-toggle');

  await expect(firstPhoto).toBeVisible();
  await expect(selectedPanel).toBeHidden();
  await firstPhoto.click();
  await expect(selectedPanel).toBeVisible();
  await expect(galleryColumns).toBeHidden();
  await expect(page).not.toHaveURL(/#photo-/);
  await expect(selectedImage).toBeVisible();
  await expect(numbers.first()).toBeVisible();
  await expect(numbers.first()).toHaveAttribute('aria-current', 'page');

  const initialImage = await selectedImage.getAttribute('src');
  await numbers.nth(1).click();
  await expect(numbers.nth(1)).toHaveAttribute('aria-current', 'page');
  await expect(selectedImage).not.toHaveAttribute('src', initialImage);

  await expect(nextZone).toBeVisible();
  await expect(previousZone).toBeVisible();
  await page.waitForFunction(() => {
    const next = document.querySelector('[data-action="next-photo"]').getBoundingClientRect();
    return Math.abs(next.right - window.innerWidth) < 2;
  });
  const hitZones = await page.locator('.gallery-selected-image').evaluate((figure) => {
    const image = figure.querySelector('img').getBoundingClientRect();
    const previous = figure.querySelector('[data-action="previous-photo"]').getBoundingClientRect();
    const next = figure.querySelector('[data-action="next-photo"]').getBoundingClientRect();
    return {
      image,
      previous,
      next,
      viewportWidth: window.innerWidth,
      previousCursor: getComputedStyle(figure.querySelector('[data-action="previous-photo"]')).cursor,
      nextCursor: getComputedStyle(figure.querySelector('[data-action="next-photo"]')).cursor,
    };
  });
  expect(hitZones.previous.x).toBeCloseTo(hitZones.image.x, 1);
  expect(hitZones.previous.right).toBeCloseTo(hitZones.image.x + hitZones.image.width / 2, 1);
  expect(hitZones.next.x).toBeCloseTo(hitZones.image.x + hitZones.image.width / 2, 1);
  expect(hitZones.next.right).toBeCloseTo(hitZones.viewportWidth, 1);
  expect(hitZones.previous.height).toBeCloseTo(hitZones.image.height, 1);
  expect(hitZones.next.height).toBeCloseTo(hitZones.image.height, 1);
  expect(hitZones.previousCursor).toContain('%23fff');
  expect(hitZones.nextCursor).toContain('%23fff');
  const tonePoints = await page.locator('.gallery-selected-image').evaluate(async (figure) => {
    const image = figure.querySelector('img');
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    const rect = image.getBoundingClientRect();
    const point = (tone) => {
      for (let y = 0; y < canvas.height; y += Math.max(1, Math.floor(canvas.height / 24))) {
        for (let x = 0; x < canvas.width / 2; x += Math.max(1, Math.floor(canvas.width / 24))) {
          const [r, g, b] = context.getImageData(x, y, 1, 1).data;
          const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
          if ((tone === 'light' && luminance >= 128) || (tone === 'dark' && luminance < 128)) {
            return {
              x: rect.left + (x / image.naturalWidth) * rect.width,
              y: rect.top + (y / image.naturalHeight) * rect.height,
              luminance,
            };
          }
        }
      }
      return null;
    };
    return { light: point('light'), dark: point('dark') };
  });
  expect(tonePoints.light).toBeTruthy();
  expect(tonePoints.dark).toBeTruthy();
  expect(tonePoints.dark.luminance).toBeLessThan(128);
  expect(tonePoints.light.luminance).toBeGreaterThanOrEqual(128);
  await page.mouse.move(tonePoints.dark.x, tonePoints.dark.y);
  await expect(page.locator('.gallery-selected-image')).toHaveAttribute('data-cursor-tone', 'dark');
  await expect(previousZone).toHaveCSS('cursor', /%23fff/);
  await page.mouse.move(tonePoints.light.x, tonePoints.light.y);
  await expect(page.locator('.gallery-selected-image')).toHaveAttribute('data-cursor-tone', 'light');
  await expect(previousZone).toHaveCSS('cursor', /%23555/);
  const secondImage = await selectedImage.getAttribute('src');
  const nextClickPoint = await page.locator('.gallery-selected-image').evaluate((figure) => {
    const image = figure.querySelector('img').getBoundingClientRect();
    return {
      x: Math.min(window.innerWidth - 5, image.right + 20),
      y: image.top + image.height / 2,
    };
  });
  await page.mouse.move(nextClickPoint.x, nextClickPoint.y);
  await page.mouse.click(nextClickPoint.x, nextClickPoint.y);
  const resampledTone = await page.locator('.gallery-selected-image').evaluate(async (figure, point) => {
    const image = figure.querySelector('img');
    await image.decode();
    const rect = image.getBoundingClientRect();
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    const x = Math.min(image.naturalWidth - 1, Math.max(0, Math.floor(((point.x - rect.left) / rect.width) * image.naturalWidth)));
    const y = Math.min(image.naturalHeight - 1, Math.max(0, Math.floor(((point.y - rect.top) / rect.height) * image.naturalHeight)));
    context.drawImage(image, x, y, 1, 1, 0, 0, 1, 1);
    const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
    const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    return luminance >= 128 ? 'light' : 'dark';
  }, nextClickPoint);
  await expect(page.locator('.gallery-selected-image')).toHaveAttribute('data-cursor-tone', resampledTone);
  await expect(nextZone).toHaveCSS('cursor', resampledTone === 'light' ? /M6\.5.*%23555|M6\.5.*%2523555/ : /M6\.5.*%23fff|M6\.5.*%2523fff/);
  await previousZone.click();
  await previousZone.click();
  await expect(selectedImage).toHaveAttribute('src', initialImage);
  await nextZone.click();
  await expect(selectedImage).toHaveAttribute('src', secondImage);

  await showThumbnails.click();
  await expect(selectedPanel).toBeHidden();
  await expect(galleryColumns).toBeVisible();
});

test('gallery selection preserves image aspect ratio and Insights tiles are uniform', async ({ page }) => {
  await page.goto('/landscape/');
  await page.locator('.gallery-columns .photo').first().click();
  const selected = page.locator('.gallery-selected-image img');
  const ratios = await selected.evaluate((image) => ({
    natural: image.naturalWidth / image.naturalHeight,
    rendered: image.clientWidth / image.clientHeight,
  }));
  expect(ratios.rendered).toBeCloseTo(ratios.natural, 3);

  await page.goto('/insights/');
  const tileRatios = await page.locator('.post-gallery-link img').evaluateAll((images) =>
    images.map((image) => image.clientWidth / image.clientHeight)
  );
  expect(new Set(tileRatios.map((ratio) => ratio.toFixed(3))).size).toBe(1);
});

test('about me art uses uncropped split layout on desktop', async ({ page }) => {
  await page.goto('/about-me-art/');
  const media = page.locator('.about-art-page .content-page-split-media');
  const body = page.locator('.about-art-page .content-page-split-body');
  const widths = await Promise.all([media, body].map((section) => section.evaluate((node) => node.getBoundingClientRect().width)));
  expect(widths[0] / (widths[0] + widths[1])).toBeGreaterThan(0.45);
  expect(widths[0] / (widths[0] + widths[1])).toBeLessThan(0.55);

  const image = page.locator('.about-art-page .content-hero');
  const ratios = await image.evaluate((img) => ({
    natural: img.naturalWidth / img.naturalHeight,
    rendered: img.clientWidth / img.clientHeight,
  }));
  expect(ratios.rendered).toBeCloseTo(ratios.natural, 2);
});

test('legacy redirect pages land on current targets', async ({ page }) => {
  await page.goto('/art/');
  await expect(page).toHaveURL(/\/index\.html$/);
  await expect(page.locator('main.gallery')).toHaveAttribute('aria-label', 'Narrative Portraiture');

  await page.goto('/work/');
  await expect(page).toHaveURL(/\/editorial-happy-hour\/$/);
  await expect(page.locator('main.gallery')).toHaveAttribute('aria-label', 'Editorial - Happy Hour');
});

test('connect page exposes mailto link and no contact form', async ({ page }) => {
  await page.goto('/connect/');
  expect(await page.locator('a[href="mailto:ryan@ryanfilgas.com"]').count()).toBeGreaterThan(0);
  await expect(page.locator('form')).toHaveCount(0);
});

test('blog index links to articles that render with shared navigation', async ({ page }) => {
  await page.goto('/insights/');
  const articleLink = page.locator('.post-list .post-gallery-link[href^="2023/"]').first();
  await expect(articleLink).toBeVisible();

  await articleLink.click();
  await expect(page).toHaveURL(/\/insights\/.+\.html$/);
  await expect(page.locator('nav.site-nav')).toBeAttached();
  await expect(page.locator('main.post h1')).toBeVisible();
});

test('blog pagination next link loads browser-safe page 2', async ({ page, request }) => {
  await page.goto('/insights/');
  const nextLink = page.locator('.post-pagination a', { hasText: 'Next' });
  await expect(nextLink).toHaveAttribute('href', '../blog/page-2.html');

  await nextLink.click();
  await expect(page).toHaveURL(/\/blog\/page-2\.html$/);
  await expect(page.locator('main.post-index .post-list .post-gallery-title').first()).toHaveText('New Directions');

  const response = await request.get('/blog/page-2.html');
  expect(response.status()).toBe(200);
  const html = await response.text();
  expect(html).toContain('New Directions');
});

test('index and blog article avoid Squarespace and Typekit network requests', async ({ page }) => {
  const blockedHosts = /(squarespace\.com|squarespace-cdn\.com|typekit\.net)/i;
  const forbidden = [];
  page.on('request', (request) => {
    const url = request.url();
    if (blockedHosts.test(url)) forbidden.push(url);
  });

  await page.goto('/index.html');
  await page.waitForLoadState('networkidle');
  await page.goto('/insights/2023/11/11/2023.html');
  await page.waitForLoadState('networkidle');

  expect(forbidden).toEqual([]);
});
