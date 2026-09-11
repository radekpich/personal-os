import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

const stamp = Date.now();
const title = `Smoke výzva ${stamp}`;
const editedTitle = `${title} upraveno`;

async function login(page) {
  await page.goto(`${frontendBaseUrl}/login`);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor({ timeout: 15_000 });
}

function attachErrorCollector(page, errors) {
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(`[console] ${msg.text()}`); });
  page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`));
  page.on('requestfailed', (req) => errors.push(`[requestfailed] ${req.url()} ${req.failure()?.errorText}`));
}

function challengeCard(page, cardTitle) {
  return page.locator('article').filter({ has: page.getByRole('heading', { name: cardTitle, exact: true }) });
}

async function createChallenge(page) {
  await page.goto(`${frontendBaseUrl}/challenges`);
  await page.getByRole('button', { name: 'Nová výzva' }).click();
  await page.getByRole('heading', { name: 'Nová výzva' }).waitFor({ timeout: 10_000 });
  await page.locator('input[placeholder="Švihadlo"]').fill(title);
  await page.getByRole('button', { name: 'Založit výzvu' }).click();
  await challengeCard(page, title).waitFor({ timeout: 15_000 });
}

async function editChallenge(page) {
  const card = challengeCard(page, title);
  await card.getByRole('button', { name: 'Upravit výzvu' }).click();
  await page.getByRole('heading', { name: 'Upravit výzvu' }).waitFor({ timeout: 10_000 });
  const titleInput = page.locator('input[placeholder="Švihadlo"]');
  const value = await titleInput.inputValue();
  if (value !== title) throw new Error(`Dialog úpravy nemá předvyplněný název: ${value}`);
  const typeInput = page.locator('label', { hasText: 'Typ' }).locator('input');
  if (!(await typeInput.isDisabled())) throw new Error('Typ výzvy by měl být v edit módu needitovatelný');
  await titleInput.fill(editedTitle);
  await page.getByRole('button', { name: 'Uložit výzvu' }).click();
  await challengeCard(page, editedTitle).waitFor({ timeout: 15_000 });
}

async function verifyNoBottomPanel(page) {
  if (await page.getByText(/^Heatmapa: /).isVisible().catch(() => false)) {
    throw new Error('Starý souhrnný panel heatmapy pod seznamem stále existuje');
  }
}

async function verifySingleExpansion(page, errors) {
  const cards = page.locator('article');
  const count = await cards.count();
  if (count < 2) {
    errors.push('[warn] méně než 2 výzvy — přeskočeno ověření jednoho rozbaleného detailu');
    return;
  }
  const first = cards.nth(0);
  const second = cards.nth(1);
  await first.getByRole('button').first().click();
  await first.getByText('Poslední zápisy').waitFor({ timeout: 10_000 });
  await second.getByRole('button').first().click();
  await second.getByText('Poslední zápisy').waitFor({ timeout: 10_000 });
  if (await first.getByText('Poslední zápisy').isVisible().catch(() => false)) {
    throw new Error('Rozbalení druhé karty nezavřelo detail první karty');
  }
  await second.getByRole('button').first().click();
  if (await second.getByText('Poslední zápisy').isVisible().catch(() => false)) {
    throw new Error('Druhý klik na kartu detail nesbalil');
  }
}

async function verifyHeatmapDisabledFutureCell(page) {
  const card = challengeCard(page, editedTitle);
  await card.getByRole('button').first().click();
  await card.getByText('Poslední zápisy').waitFor({ timeout: 10_000 });
  const disabledCells = card.locator('[aria-label*="nelze zapsat"]');
  const disabledCount = await disabledCells.count();
  if (disabledCount === 0) throw new Error('V heatmapě nejsou žádné needitovatelné (budoucí/staré) buňky');
  const isDisabled = await disabledCells.first().isDisabled();
  if (!isDisabled) throw new Error('Needitovatelná buňka heatmapy není disabled');
  await card.getByRole('button').first().click();
}

async function cleanup(page) {
  const card = challengeCard(page, editedTitle);
  await card.getByRole('button', { name: 'Smazat výzvu' }).click();
  await page.getByRole('heading', { name: /^Smazat výzvu/ }).waitFor({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Smazat výzvu', exact: true }).last().click();
  await challengeCard(page, editedTitle).waitFor({ state: 'detached', timeout: 15_000 });
}

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 900 }, isMobile: true });
  const errors = [];
  attachErrorCollector(page, errors);
  try {
    await login(page);
    await createChallenge(page);
    await verifyNoBottomPanel(page);
    await editChallenge(page);
    await verifySingleExpansion(page, errors);
    await verifyHeatmapDisabledFutureCell(page);
    await cleanup(page);
    console.log(JSON.stringify({ ok: errors.length === 0, errors }, null, 2));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await run();
