import { chromium } from '@playwright/test';

const baseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3000';
const email = process.env.PHASE5_E2E_EMAIL;
const password = process.env.PHASE5_E2E_PASSWORD;

if (!email || !password) {
  throw new Error('Set PHASE5_E2E_EMAIL and PHASE5_E2E_PASSWORD');
}

const stamp = Date.now();

async function login(page) {
  await page.goto(`${baseUrl}/login`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
}

async function runDesktopSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 950 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (error) => errors.push(error.message));

  await login(page);
  await page.getByRole('link', { name: 'Návyky' }).first().click();
  await page.getByRole('heading', { name: 'Návyky a výzvy' }).waitFor();

  const dailyTitle = `Smoke švihadlo ${stamp}`;
  await page.getByLabel('Název').fill(dailyTitle);
  await page.getByLabel('Popis').fill('Smoke daily action s hodnotou');
  await page.getByLabel('Cíl dní').fill('30');
  await page.getByLabel('Grace dny').fill('1');
  await page.getByRole('button', { name: 'Založit výzvu' }).click();
  await page.locator('h3', { hasText: dailyTitle }).waitFor();

  const dailyCard = page.locator('article', { hasText: dailyTitle }).first();
  await dailyCard.getByRole('button', { name: /Zapsat dnešek/ }).click();
  await dailyCard.getByText('1', { exact: true }).first().waitFor();
  await dailyCard.getByText('rekord 1 dní').waitFor();
  await page.getByText('Heatmapa:').waitFor();

  const abstinenceTitle = `Smoke bez cukru ${stamp}`;
  await page.getByLabel('Název').fill(abstinenceTitle);
  await page.getByLabel('Typ').selectOption('abstinence');
  await page.getByRole('button', { name: 'Založit výzvu' }).click();
  await page.locator('h3', { hasText: abstinenceTitle }).waitFor();
  const abstinenceCard = page.locator('article', { hasText: abstinenceTitle }).first();
  await abstinenceCard.getByRole('button', { name: /Zapsat relaps/ }).click();
  await abstinenceCard.getByText('0', { exact: true }).first().waitFor();

  await page.screenshot({ path: '/tmp/personal-os-phase5-desktop.png', fullPage: true });
  if (errors.length) throw new Error(`Browser console errors: ${errors.join('\n')}`);
  await page.close();
  return { dailyTitle, abstinenceTitle, desktopScreenshot: '/tmp/personal-os-phase5-desktop.png' };
}

async function runMobileSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  await login(page);
  await page.getByRole('link', { name: 'Návyky' }).click();
  await page.getByRole('heading', { name: 'Návyky a výzvy' }).waitFor();
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (!bottomVisible) throw new Error('Mobile bottom nav is not visible on challenges page');
  await page.locator('[aria-label="Roční heatmapa návyků"]').first().waitFor({ timeout: 10000 }).catch(() => undefined);
  await page.screenshot({ path: '/tmp/personal-os-phase5-mobile.png', fullPage: true });
  await page.close();
  return { mobileScreenshot: '/tmp/personal-os-phase5-mobile.png' };
}

const browser = await chromium.launch();
try {
  const desktop = await runDesktopSmoke(browser);
  const mobile = await runMobileSmoke(browser);
  console.log(JSON.stringify({ ok: true, ...desktop, ...mobile }, null, 2));
} finally {
  await browser.close();
}
