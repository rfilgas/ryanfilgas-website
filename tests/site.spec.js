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

test('gallery lightbox opens, advances, shows numbers, and closes from keyboard', async ({ page }) => {
  await page.goto('/index.html');

  const firstPhoto = page.locator('.gallery-columns .photo').first();
  const viewer = page.locator('.viewer');
  const viewerImage = page.locator('.viewer-image img');
  const numbers = page.locator('.viewer-numbers button');

  await expect(firstPhoto).toBeVisible();
  await firstPhoto.click();
  await expect(viewer).toHaveClass(/is-open/);
  await expect(viewer).toBeVisible();
  await expect(page).toHaveURL(/#photo-1$/);
  await expect(numbers.first()).toBeVisible();
  await expect(numbers.first()).toHaveAttribute('aria-current', 'true');

  const initialImage = await viewerImage.getAttribute('src');
  await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/#photo-2$/);
  await expect(numbers.nth(1)).toHaveAttribute('aria-current', 'true');
  await expect(viewerImage).not.toHaveAttribute('src', initialImage);

  await page.keyboard.press('Escape');
  await expect(viewer).toBeHidden();
  await expect(page).not.toHaveURL(/#photo-/);
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
