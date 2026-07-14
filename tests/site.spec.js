const { test, expect } = require('@playwright/test');

const pagesFromNav = [
  'index.html',
  'landscape.html',
  'arial-silks.html',
  'free-flight.html',
  'digital-art.html',
  'editorial-happy-hour.html',
  'architecture-interior.html',
  'architecture-exterior.html',
  'about-me-art.html',
  'about-software-engineering.html',
  'connect.html',
  'blog-insights.html',
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

test('legacy redirect pages land on current targets', async ({ page }) => {
  await page.goto('/art.html');
  await expect(page).toHaveURL(/\/index\.html$/);
  await expect(page.locator('main.gallery')).toHaveAttribute('aria-label', 'Narrative Portraiture');

  await page.goto('/work.html');
  await expect(page).toHaveURL(/\/editorial-happy-hour\.html$/);
  await expect(page.locator('main.gallery')).toHaveAttribute('aria-label', 'Editorial - Happy Hour');
});

test('connect page exposes mailto link and no contact form', async ({ page }) => {
  await page.goto('/connect.html');
  expect(await page.locator('a[href="mailto:ryan@ryanfilgas.com"]').count()).toBeGreaterThan(0);
  await expect(page.locator('form')).toHaveCount(0);
});

test('blog index links to articles that render with shared navigation', async ({ page }) => {
  await page.goto('/blog-insights.html');
  const articleLink = page.locator('.post-list h2 a[href^="insights/"]').first();
  await expect(articleLink).toBeVisible();

  await articleLink.click();
  await expect(page).toHaveURL(/\/insights\/.+\.html$/);
  await expect(page.locator('nav.site-nav')).toBeAttached();
  await expect(page.locator('main.post h1')).toBeVisible();
});

test('blog pagination next link loads browser-safe page 2', async ({ page, request }) => {
  await page.goto('/blog-insights.html');
  const nextLink = page.locator('.post-pagination a', { hasText: 'Next' });
  await expect(nextLink).toHaveAttribute('href', 'blog/page-2.html');

  await nextLink.click();
  await expect(page).toHaveURL(/\/blog\/page-2\.html$/);
  await expect(page.locator('main.post-index .post-list h2 a').first()).toHaveText('New Directions');

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
