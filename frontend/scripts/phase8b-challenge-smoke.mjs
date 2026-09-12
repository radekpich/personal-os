import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

const stamp = Date.now();
const title = `Smoke výzva ${stamp}`;
const editedTitle = `${title} upraveno`;
const pragueFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Prague', year: 'numeric', month: '2-digit', day: '2-digit' });
function pragueDate(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return pragueFormatter.format(date);
}
function czechDateLong(value) {
  return new Intl.DateTimeFormat('cs-CZ', { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00`));
}
const yesterday = pragueDate(-1);

async function login(page) {
  await page.goto(`${frontendBaseUrl}/login`);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor({ timeout: 15_000 });
}

async function apiJson(page, path, options = {}) {
  const method = options.method ?? 'GET';
  const cookies = await page.context().cookies(apiBaseUrl);
  const csrf = cookies.find((cookie) => cookie.name === 'csrf_token')?.value;
  const headers = { 'Content-Type': 'application/json', ...(options.headers ?? {}) };
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase()) && csrf) headers['X-CSRF-Token'] = csrf;
  const response = await page.request.fetch(`${apiBaseUrl}${path}`, { ...options, method, headers });
  if (!response.ok()) throw new Error(`${method} ${path} failed: ${response.status()} ${await response.text()}`);
  if (response.status() === 204) return null;
  return response.json();
}

function attachErrorCollector(page, errors) {
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !text.includes('404 (Not Found)')) errors.push(`[console] ${text}`);
  });
  page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`));
  page.on('requestfailed', (req) => {
    const failure = req.failure()?.errorText ?? '';
    if (req.url().includes('/challenges/') && failure.includes('ERR_ABORTED')) return;
    errors.push(`[requestfailed] ${req.url()} ${failure}`);
  });
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
  const list = await apiJson(page, '/challenges');
  const challenge = list.items.find((item) => item.title === title);
  if (!challenge) throw new Error('Created challenge was not returned by API');
  await apiJson(page, `/challenges/${challenge.id}`, {
    method: 'PATCH',
    data: { started_at: `${yesterday}T00:00:00+01:00` },
  });
  await page.reload();
  await challengeCard(page, title).waitFor({ timeout: 15_000 });
  return challenge.id;
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

async function verifyYesterdayHeatmapRecalculatesStreak(page, challengeId) {
  const card = challengeCard(page, editedTitle);
  await card.getByRole('button').first().click();
  await card.getByText('Poslední zápisy').waitFor({ timeout: 10_000 });
  await Promise.all([
    page.waitForResponse((response) => response.url().includes(`/challenges/${challengeId}/check-in`) && response.request().method() === 'POST' && response.ok()),
    card.getByLabel(czechDateLong(yesterday), { exact: true }).click(),
  ]);
  const stats = await apiJson(page, `/challenges/${challengeId}/stats`);
  if (stats.current_streak !== 1) throw new Error(`Šňůra po včerejším zápisu není 1: ${JSON.stringify(stats)}`);
  await card.locator('div').filter({ hasText: 'Aktuální šňůra' }).getByText('1 den').first().waitFor({ timeout: 10_000 });
  await card.getByRole('button').first().click();
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
  const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
  const errors = [];
  attachErrorCollector(page, errors);
  try {
    await login(page);
    const challengeId = await createChallenge(page);
    await verifyNoBottomPanel(page);
    await editChallenge(page);
    await verifySingleExpansion(page, errors);
    await verifyYesterdayHeatmapRecalculatesStreak(page, challengeId);
    await verifyHeatmapDisabledFutureCell(page);
    await cleanup(page);
    console.log(JSON.stringify({ ok: errors.length === 0, errors }, null, 2));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await run();
