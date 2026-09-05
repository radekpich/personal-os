import { chromium } from '@playwright/test';

const baseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3000';
const email = process.env.PHASE4_E2E_EMAIL;
const password = process.env.PHASE4_E2E_PASSWORD;

if (!email || !password) {
  throw new Error('Set PHASE4_E2E_EMAIL and PHASE4_E2E_PASSWORD');
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
  await page.getByRole('link', { name: 'Vize' }).first().click();
  await page.getByRole('heading', { name: 'Strom dlouhodobých cílů' }).waitFor();

  const rootTitle = `Smoke sen ${stamp}`;
  const childTitle = `Smoke milník ${stamp}`;
  await page.getByLabel('Název').fill(rootTitle);
  await page.getByLabel('Popis Markdown').fill('**Smoke** dlouhodobá vize');
  await page.getByRole('button', { name: 'Založit vizi' }).click();
  await page.locator('h3', { hasText: rootTitle }).waitFor();

  await page.getByRole('button', { name: 'Nová vize' }).click();
  await page.getByLabel('Název').fill(childTitle);
  await page.getByLabel('Horizont').selectOption('quarter');
  await page.getByRole('button', { name: 'Založit vizi' }).click();
  await page.locator('h3', { hasText: childTitle }).waitFor();

  const childCard = page.locator('h3', { hasText: childTitle }).locator('xpath=ancestor::article[1]');
  const rootCard = page.locator('h3', { hasText: rootTitle }).locator('xpath=ancestor::article[1]');
  await childCard.dragTo(rootCard);
  await page.locator('h3', { hasText: childTitle }).waitFor();

  const taskTitle = `Smoke úkol pro vizi ${stamp}`;
  await page.getByLabel('Rychlý zápis úkolu').fill(taskTitle);
  await page.keyboard.press('Enter');
  await page.getByRole('link', { name: 'Inbox' }).first().click();
  await page.getByRole('button', { name: taskTitle }).waitFor();
  await page.getByRole('button', { name: 'Otevřít detail' }).first().click();
  await page.getByRole('heading', { name: 'Detail úkolu' }).waitFor();
  await page.getByLabel('Vize / cíl').selectOption({ label: childTitle });
  await page.getByRole('button', { name: 'Uložit změny' }).click();
  await page.getByText(`🎯 ${childTitle}`).waitFor();

  await page.getByRole('link', { name: 'Vize' }).first().click();
  await page.locator('h3', { hasText: childTitle }).waitFor();
  await page.getByText('0/1 úkolů').first().waitFor();
  await page.screenshot({ path: '/tmp/personal-os-phase4-desktop.png', fullPage: true });

  if (errors.length) throw new Error(`Browser console errors: ${errors.join('\n')}`);
  await page.close();
  return { rootTitle, childTitle, taskTitle, desktopScreenshot: '/tmp/personal-os-phase4-desktop.png' };
}

async function runMobileSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 375, height: 812 }, isMobile: true });
  await login(page);
  await page.getByRole('link', { name: 'Vize' }).click();
  await page.getByRole('heading', { name: 'Strom dlouhodobých cílů' }).waitFor();
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (!bottomVisible) throw new Error('Mobile bottom nav is not visible on visions page');
  await page.screenshot({ path: '/tmp/personal-os-phase4-mobile.png', fullPage: true });
  await page.close();
  return { mobileScreenshot: '/tmp/personal-os-phase4-mobile.png' };
}

const browser = await chromium.launch();
try {
  const desktop = await runDesktopSmoke(browser);
  const mobile = await runMobileSmoke(browser);
  console.log(JSON.stringify({ ok: true, ...desktop, ...mobile }, null, 2));
} finally {
  await browser.close();
}
