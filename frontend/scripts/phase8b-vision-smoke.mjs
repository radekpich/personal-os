import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

const stamp = Date.now();
const title = `Smoke vize ${stamp}`;
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

function visionCard(page, cardTitle) {
  return page.locator('article').filter({ has: page.getByRole('heading', { name: cardTitle, exact: true }) });
}

async function createVision(page) {
  await page.goto(`${frontendBaseUrl}/visions`);
  await page.getByRole('button', { name: 'Nová vize' }).click();
  await page.getByRole('heading', { name: 'Nová vize' }).waitFor({ timeout: 10_000 });
  await page.locator('input[name="title"]').fill(title);
  await page.locator('textarea[name="description"]').fill('**Tučná smoke vize** <script>alert(1)</script>');
  await page.getByRole('button', { name: 'Založit vizi' }).click();
  await visionCard(page, title).waitFor({ timeout: 15_000 });
}

async function editVision(page) {
  const card = visionCard(page, title);
  await card.getByRole('button', { name: 'Upravit vizi' }).click();
  await page.getByRole('heading', { name: 'Upravit vizi' }).waitFor({ timeout: 10_000 });
  const titleInput = page.locator('input[name="title"]');
  const value = await titleInput.inputValue();
  if (value !== title) throw new Error(`Dialog úpravy vize nemá předvyplněný název: ${value}`);
  await titleInput.fill(editedTitle);
  await page.getByRole('button', { name: 'Uložit vizi' }).click();
  await visionCard(page, editedTitle).waitFor({ timeout: 15_000 });
}

async function verifyExpandableDetail(page) {
  const cards = page.locator('article');
  const target = visionCard(page, editedTitle);
  await target.getByRole('button', { name: `Detail vize ${editedTitle}` }).click();
  await target.getByText('Popis').waitFor({ timeout: 10_000 });
  await target.getByText('Tučná smoke vize').last().waitFor({ timeout: 10_000 });
  if (await target.getByText('script').isVisible().catch(() => false)) throw new Error('Markdown detail vize ukazuje nebezpečné script HTML');

  if (await cards.count() > 1) {
    const other = cards.filter({ hasNot: page.getByRole('heading', { name: editedTitle, exact: true }) }).first();
    await other.getByRole('button', { name: /^Detail vize / }).click();
    if (await target.getByText('Popis').isVisible().catch(() => false)) throw new Error('Rozbalení druhé vize nezavřelo první detail');
  } else {
    await target.getByRole('button', { name: `Detail vize ${editedTitle}` }).click();
    if (await target.getByText('Popis').isVisible().catch(() => false)) throw new Error('Druhý klik vizi nesbalil');
  }
}

async function verifyNoInlineForm(page) {
  await page.goto(`${frontendBaseUrl}/visions`);
  if (await page.locator('main.workspace form').count() > 0) throw new Error('Na stránce vizí zůstal vestavěný formulář');
}

async function cleanup(page) {
  await page.goto(`${frontendBaseUrl}/visions`);
  const card = visionCard(page, editedTitle);
  if (!(await card.count())) return;
  await card.getByRole('button', { name: 'Smazat vizi' }).click();
  await page.getByRole('heading', { name: 'Smazat vizi' }).waitFor({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Smazat vizi', exact: true }).click();
  await card.waitFor({ state: 'detached', timeout: 15_000 }).catch(() => undefined);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
  const errors = [];
  attachErrorCollector(page, errors);
  try {
    await login(page);
    await verifyNoInlineForm(page);
    await createVision(page);
    await editVision(page);
    await verifyExpandableDetail(page);
    await cleanup(page);
    console.log(JSON.stringify({ ok: errors.length === 0, errors }, null, 2));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await run();
