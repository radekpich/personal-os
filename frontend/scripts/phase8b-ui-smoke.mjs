import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

async function login(page) {
  await page.goto(`${frontendBaseUrl}/login`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
}

function attachErrorCollector(page, errors) {
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(`[console] ${msg.text()}`); });
  page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`));
  page.on('requestfailed', (req) => errors.push(`[requestfailed] ${req.url()} ${req.failure()?.errorText}`));
}

async function runDesktop(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 950 } });
  const errors = [];
  attachErrorCollector(page, errors);
  await login(page);

  await page.goto(`${frontendBaseUrl}/challenges`);
  await page.getByRole('heading', { name: 'Návyky a výzvy' }).waitFor();
  await page.getByRole('button', { name: 'Nová výzva' }).click();
  await page.getByRole('heading', { name: 'Nová výzva' }).waitFor();
  const stamp = Date.now();
  const challengeTitle = `Smoke výzva ${stamp}`;
  await page.getByPlaceholder('Švihadlo').fill(challengeTitle);
  await page.getByRole('button', { name: 'Uložit' }).click();
  await page.getByText(challengeTitle).first().waitFor({ timeout: 10_000 });
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-desktop-challenges.png', fullPage: true });

  await page.goto(`${frontendBaseUrl}/tasks`);
  await page.getByLabel('Otevřít plný dialog úkolu').click();
  await page.getByRole('heading', { name: 'Nový úkol' }).waitFor();
  await page.getByLabel('Název').fill(`Smoke úkol ${stamp}`);
  await page.getByRole('button', { name: 'Zrušit' }).click();
  const desktopContextFilter = await page.locator('select').nth(2).evaluate((select) => select.selectedOptions[0]?.textContent?.trim());
  if (desktopContextFilter !== 'Všechna místa') throw new Error(`Unexpected desktop context filter label: ${desktopContextFilter}`);
  await page.getByText('Místo nebo nástroj, kde úkol zvládnu').waitFor();
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-desktop-tasks.png', fullPage: true });

  await page.goto(`${frontendBaseUrl}/diary`);
  await page.getByRole('button', { name: 'Nový zápis' }).click();
  await page.getByRole('heading', { name: 'Nový zápis' }).waitFor();
  const noteTitle = `Smoke zápis ${stamp}`;
  await page.getByPlaceholder('Název').fill(noteTitle);
  await page.getByRole('button', { name: 'Uložit' }).click();
  await page.getByText(noteTitle).first().waitFor({ timeout: 10_000 });
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-desktop-diary.png', fullPage: true });

  await page.goto(`${frontendBaseUrl}/settings`);
  await page.getByRole('heading', { name: 'Vzhled' }).waitFor();
  await page.getByText('Kategorie').first().waitFor();
  await page.getByText('Místa').first().waitFor();
  await page.getByText('Tagy').first().waitFor();
  await page.getByRole('button', { name: 'Tmavý' }).click();
  await page.waitForTimeout(300);
  await page.getByRole('button', { name: 'Podle systému' }).click();
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-desktop-settings.png', fullPage: true });

  await page.close();
  return errors;
}

async function runMobile(browser) {
  const page = await browser.newPage({ viewport: { width: 375, height: 800 }, isMobile: true });
  const errors = [];
  attachErrorCollector(page, errors);
  await login(page);

  await page.goto(`${frontendBaseUrl}/challenges`);
  await page.getByRole('button', { name: 'Nová výzva' }).click();
  await page.getByRole('heading', { name: 'Nová výzva' }).waitFor();
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-mobile-challenges.png', fullPage: true });
  await page.getByRole('button', { name: 'Zrušit' }).click();

  await page.goto(`${frontendBaseUrl}/tasks`);
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (!bottomVisible) throw new Error('Mobile bottom nav not visible on /tasks');
  const mobileContextFilter = await page.locator('select').nth(2).evaluate((select) => select.selectedOptions[0]?.textContent?.trim());
  if (mobileContextFilter !== 'Všechna místa') throw new Error(`Unexpected mobile context filter label: ${mobileContextFilter}`);
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-mobile-tasks.png', fullPage: true });

  await page.goto(`${frontendBaseUrl}/diary`);
  await page.getByRole('button', { name: 'Nový zápis' }).click();
  await page.getByRole('heading', { name: 'Nový zápis' }).waitFor();
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-mobile-diary.png', fullPage: true });
  await page.getByRole('button', { name: 'Zrušit' }).click();

  await page.goto(`${frontendBaseUrl}/settings`);
  await page.getByRole('heading', { name: 'Vzhled' }).waitFor();
  await page.screenshot({ path: '/tmp/personal-os-8b-ui-mobile-settings.png', fullPage: true });

  await page.close();
  return errors;
}

const browser = await chromium.launch();
try {
  const desktopErrors = await runDesktop(browser);
  const mobileErrors = await runMobile(browser);
  const errors = [...desktopErrors, ...mobileErrors];
  console.log(JSON.stringify({ ok: errors.length === 0, errors }, null, 2));
  if (errors.length) process.exitCode = 1;
} finally {
  await browser.close();
}
