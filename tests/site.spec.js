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

test('index and blog article avoid legacy-platform and Typekit network requests', async ({ page }) => {
  const blockedHosts = /(legacy-platform\.com|legacy-cdn\.com|typekit\.net)/i;
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
