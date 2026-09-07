import { chromium } from '@playwright/test';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const baseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3000';
const email = process.env.PHASE6B_E2E_EMAIL;
const password = process.env.PHASE6B_E2E_PASSWORD;

if (!email || !password) {
  throw new Error('Set PHASE6B_E2E_EMAIL and PHASE6B_E2E_PASSWORD');
}

const stamp = Date.now();

// Smallest valid 1x1 transparent PNG, used as a real image attachment fixture.
const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

function writeFixtureImage() {
  const dir = mkdtempSync(join(tmpdir(), 'personal-os-phase6b-'));
  const path = join(dir, `smoke-attachment-${stamp}.png`);
  writeFileSync(path, Buffer.from(PNG_BASE64, 'base64'));
  return path;
}

async function login(page) {
  await page.goto(`${baseUrl}/login`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
}

async function goToDiary(page) {
  await page.getByRole('link', { name: 'Deník' }).first().click();
  await page.getByRole('heading', { name: 'Deník a poznámky' }).waitFor();
}

async function runDesktopSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 950 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (error) => errors.push(error.message));

  await login(page);
  await goToDiary(page);

  const title = `Smoke deník ${stamp}`;
  const body = `Dnešní smoke zápis ${stamp} — ověření persistence.`;

  await page.getByRole('button', { name: 'Nový zápis' }).click();
  await page.getByPlaceholder('Název').fill(title);
  await page.getByPlaceholder('Markdown zápis…').fill(body);
  await page.getByRole('button', { name: 'Uložit', exact: true }).click();
  await page.locator('h3', { hasText: title }).waitFor();
  await page.getByText('Upravit zápis').waitFor();

  // Verify persistence: navigate away and back, then re-open the note.
  await page.getByRole('link', { name: 'Přehled' }).first().click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
  await goToDiary(page);
  await page.locator('h3', { hasText: title }).click();
  const bodyValue = await page.getByPlaceholder('Markdown zápis…').inputValue();
  if (bodyValue !== body) {
    throw new Error(`Diary note body did not persist. Expected "${body}", got "${bodyValue}"`);
  }
  const titleValue = await page.getByPlaceholder('Název').inputValue();
  if (titleValue !== title) {
    throw new Error(`Diary note title did not persist. Expected "${title}", got "${titleValue}"`);
  }

  // Upload an image attachment through the reused attachment uploader UI.
  const fixturePath = writeFixtureImage();
  const fixtureName = fixturePath.split('/').pop();
  await page.locator('input[type="file"]').setInputFiles(fixturePath);
  await page.getByText('Příloha nahraná.').waitFor({ timeout: 15000 });
  await page.getByText(fixtureName).waitFor({ timeout: 15000 });

  // Verify grid/lightbox/download-visible state.
  const attachmentCard = page.locator('article', { hasText: fixtureName });
  await attachmentCard.waitFor();
  await attachmentCard.getByRole('button').first().click();
  await page.getByText('Stáhnout').waitFor();
  const downloadHref = await page.getByRole('link', { name: /Stáhnout/ }).getAttribute('href');
  if (!downloadHref || !downloadHref.includes('/attachments/')) {
    throw new Error(`Unexpected attachment download href: ${downloadHref}`);
  }
  await page.keyboard.press('Escape');

  // Unlink the attachment from the note and confirm it's gone from the grid.
  await attachmentCard.getByRole('button', { name: /Odpojit/ }).click();
  await page.getByText('Zatím žádné přílohy.').waitFor({ timeout: 15000 });

  await page.screenshot({ path: '/tmp/personal-os-phase6b-desktop.png', fullPage: true });
  if (errors.length) throw new Error(`Browser console errors: ${errors.join('\n')}`);
  await page.close();
  return {
    diaryTitle: title,
    attachmentFile: fixtureName,
    downloadHref,
    desktopScreenshot: '/tmp/personal-os-phase6b-desktop.png',
  };
}

async function runMobileSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  await login(page);
  await goToDiary(page);
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (!bottomVisible) throw new Error('Mobile bottom nav is not visible on diary page');
  await page.screenshot({ path: '/tmp/personal-os-phase6b-mobile.png', fullPage: true });
  await page.close();
  return { mobileScreenshot: '/tmp/personal-os-phase6b-mobile.png' };
}

const browser = await chromium.launch();
try {
  const desktop = await runDesktopSmoke(browser);
  const mobile = await runMobileSmoke(browser);
  console.log(JSON.stringify({ ok: true, ...desktop, ...mobile }, null, 2));
} finally {
  await browser.close();
}
