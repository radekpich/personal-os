import { chromium } from '@playwright/test';

const baseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3000';
const email = process.env.PHASE3_E2E_EMAIL;
const password = process.env.PHASE3_E2E_PASSWORD;

if (!email || !password) {
  throw new Error('Set PHASE3_E2E_EMAIL and PHASE3_E2E_PASSWORD');
}

async function runDesktopSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));

  await page.goto(`${baseUrl}/login`);
  await page.context().clearCookies();
  await page.reload();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();

  const title = `Smoke úkol ${Date.now()}`;
  await page.getByLabel('Rychlý zápis úkolu').fill(title);
  await page.keyboard.press('Enter');
  await page.getByRole('link', { name: 'Inbox' }).first().click();
  await page.getByRole('button', { name: title }).waitFor();
  await page.getByRole('button', { name: 'Otevřít detail' }).first().click();
  await page.getByRole('heading', { name: 'Detail úkolu' }).waitFor();
  await page.getByRole('button', { name: 'Uložit změny' }).click();
  await page.getByRole('button', { name: 'Dokončit úkol' }).first().click();
  await page.getByText('Nic tu není').waitFor();

  await page.getByRole('link', { name: 'Nastavení' }).first().click();
  await page.getByRole('heading', { name: 'Kalendářový odkaz' }).waitFor();
  const calendarInput = page.locator('input[readonly]').last();
  const before = await calendarInput.inputValue();
  await page.getByRole('button', { name: 'Přegenerovat' }).click();
  await page.getByText('Token byl přegenerovaný').waitFor();
  const after = await calendarInput.inputValue();
  if (before === after) throw new Error('Calendar token did not change');

  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+K' : 'Control+K');
  await page.getByRole('heading', { name: 'Command palette' }).waitFor();
  await page.screenshot({ path: '/tmp/personal-os-phase3-desktop.png', fullPage: true });

  if (errors.length) throw new Error(`Browser console errors: ${errors.join('\n')}`);
  await page.close();
  return { quickTask: title, desktopScreenshot: '/tmp/personal-os-phase3-desktop.png' };
}

async function runMobileSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 375, height: 812 }, isMobile: true });
  await page.goto(`${baseUrl}/login`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
  const sidebarVisible = await page.locator('.sidebar').isVisible();
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (sidebarVisible || !bottomVisible) throw new Error(`Mobile nav responsive check failed: sidebar=${sidebarVisible}, bottom=${bottomVisible}`);
  await page.screenshot({ path: '/tmp/personal-os-phase3-mobile.png', fullPage: true });
  await page.close();
  return { mobileScreenshot: '/tmp/personal-os-phase3-mobile.png' };
}

const browser = await chromium.launch();
try {
  const desktop = await runDesktopSmoke(browser);
  const mobile = await runMobileSmoke(browser);
  console.log(JSON.stringify({ ok: true, ...desktop, ...mobile }, null, 2));
} finally {
  await browser.close();
}
