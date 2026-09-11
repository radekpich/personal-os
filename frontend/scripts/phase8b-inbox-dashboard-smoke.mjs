import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

const stamp = Date.now();
const today = new Date().toISOString().slice(0, 10);
const tomorrowDate = new Date();
tomorrowDate.setDate(tomorrowDate.getDate() + 1);
const tomorrow = tomorrowDate.toISOString().slice(0, 10);

async function login(page) {
  await page.goto(`${frontendBaseUrl}/login`);
  if (await page.getByRole('heading', { name: 'Přehled' }).isVisible().catch(() => false)) return;
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
  const response = await page.request.fetch(`${apiBaseUrl}${path}`, {
    ...options,
    method,
    headers,
  });
  if (!response.ok()) throw new Error(`${method} ${path} failed: ${response.status()} ${await response.text()}`);
  if (response.status() === 204) return null;
  return response.json();
}

async function seed(page) {
  const category = await apiJson(page, '/categories', {
    method: 'POST',
    data: { name: `Smoke kat ${stamp}`, color: '#2563EB', icon: 'check' },
  });
  const context = await apiJson(page, '/contexts', {
    method: 'POST',
    data: { name: `Smoke kde ${stamp}`, color: '#2563EB', icon: 'pin' },
  });
  const common = { category_id: category.id, context_id: context.id };
  const todayTask = await apiJson(page, '/tasks', {
    method: 'POST',
    data: { title: `Smoke dnes ${stamp}`, status: 'todo', priority: 'high', due_date: today, due_time: '00:01', ...common },
  });
  const tomorrowTask = await apiJson(page, '/tasks', {
    method: 'POST',
    data: { title: `Smoke zítra ${stamp}`, status: 'todo', priority: 'medium', due_date: tomorrow, due_time: '00:01', ...common },
  });
  const inboxTask = await apiJson(page, '/tasks', {
    method: 'POST',
    data: { title: `Smoke inbox ${stamp}`, source: 'email', source_detail: 'nevesta@example.com' },
  });
  await apiJson(page, '/notes', {
    method: 'POST',
    data: { title: `Smoke deník ${stamp}`, body: 'Regresní zápis pro dashboard.', kind: 'diary', entry_date: today },
  });
  return { category, context, todayTask, tomorrowTask, inboxTask };
}

function attachErrorCollector(page, errors) {
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(`[console] ${msg.text()}`); });
  page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`));
  page.on('requestfailed', (req) => errors.push(`[requestfailed] ${req.url()} ${req.failure()?.errorText}`));
}

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 900 }, isMobile: true });
  const errors = [];
  attachErrorCollector(page, errors);
  try {
    await login(page);
    const data = await seed(page);

    await page.goto(`${frontendBaseUrl}/dashboard`);
    const main = page.locator('main');
    await main.getByText('Dnes').first().waitFor();
    await main.getByText('Po termínu').first().waitFor();
    await main.getByText('Inbox').first().waitFor();
    await main.getByText(data.todayTask.title).waitFor({ timeout: 15_000 });
    await main.getByText(data.tomorrowTask.title).waitFor({ timeout: 15_000 });
    await main.getByText(data.inboxTask.title).waitFor({ state: 'detached', timeout: 3_000 }).catch(() => undefined);
    await page.locator('article').filter({ hasText: data.todayTask.title }).getByRole('button', { name: 'Dokončit úkol' }).click();
    await main.getByText(data.todayTask.title).waitFor({ state: 'detached', timeout: 15_000 });
    await page.screenshot({ path: '/tmp/personal-os-8b-dashboard-smoke.png', fullPage: true });

    await page.goto(`${frontendBaseUrl}/tasks`);
    await page.getByText(data.inboxTask.title).waitFor({ state: 'detached', timeout: 5_000 }).catch(() => undefined);
    if (await page.getByText(data.inboxTask.title).isVisible().catch(() => false)) throw new Error('Inbox item leaked into /tasks');

    await page.goto(`${frontendBaseUrl}/inbox`);
    await page.locator('main').getByRole('heading', { name: 'Inbox' }).first().waitFor();
    await page.getByRole('heading', { name: /E-mail/ }).waitFor({ timeout: 15_000 });
    await page.getByText(data.inboxTask.title).waitFor({ timeout: 15_000 });
    const inboxArticle = page.locator('article').filter({ hasText: data.inboxTask.title });
    await inboxArticle.getByText('nevesta@example.com').waitFor();
    await Promise.all([
      page.waitForResponse((response) => response.url().includes(`/tasks/${data.inboxTask.id}`) && response.request().method() === 'PATCH' && response.ok()),
      page.getByLabel(`Kategorie pro ${data.inboxTask.title}`).selectOption(data.category.id),
    ]);
    await inboxArticle.getByRole('button', { name: /Zpracovat/ }).click();
    await page.getByRole('heading', { name: 'Detail úkolu' }).waitFor({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Zrušit' }).click();
    await Promise.all([
      page.waitForResponse((response) => response.url().includes(`/tasks/${data.inboxTask.id}`) && response.request().method() === 'PATCH' && response.ok()),
      page.getByLabel(`Kde pro ${data.inboxTask.title}`).selectOption(data.context.id),
    ]);
    await page.screenshot({ path: '/tmp/personal-os-8b-inbox-smoke.png', fullPage: true });

    console.log(JSON.stringify({ ok: errors.length === 0, errors, seeded: data }, null, 2));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await run();
