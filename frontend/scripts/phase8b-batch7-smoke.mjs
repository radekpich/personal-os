import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

const stamp = Date.now();
const pragueFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Prague', year: 'numeric', month: '2-digit', day: '2-digit' });
function pragueDate(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return pragueFormatter.format(date);
}
const today = pragueDate();
const tomorrow = pragueDate(1);

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
  const response = await page.request.fetch(`${apiBaseUrl}${path}`, { ...options, method, headers });
  if (!response.ok()) throw new Error(`${method} ${path} failed: ${response.status()} ${await response.text()}`);
  if (response.status() === 204) return null;
  return response.json();
}

async function seed(page) {
  const category = await apiJson(page, '/categories', { method: 'POST', data: { name: `Batch7 kat ${stamp}`, color: '#2563EB', icon: 'check' } });
  const context = await apiJson(page, '/contexts', { method: 'POST', data: { name: `Batch7 kde ${stamp}`, color: '#2563EB', icon: 'pin' } });
  const common = { category_id: category.id, context_id: context.id };
  const tomorrowTask = await apiJson(page, '/tasks', { method: 'POST', data: { title: `Batch7 zítra ${stamp}`, status: 'todo', priority: 'medium', due_date: tomorrow, ...common } });
  const inboxTasks = [];
  for (let i = 1; i <= 3; i += 1) {
    inboxTasks.push(await apiJson(page, '/tasks', { method: 'POST', data: { title: `Batch7 inbox ${i} ${stamp}`, source: i === 1 ? 'telegram' : 'email', source_detail: `bulk-${i}@example.test` } }));
  }
  const challenge = await apiJson(page, '/challenges', { method: 'POST', data: { title: `Batch7 návyk ${stamp}`, type: 'daily_action', started_at: today, schedule_rrule: 'FREQ=DAILY', icon: '✅', color: '#16A34A' } });
  return { category, context, tomorrowTask, inboxTasks, challenge };
}

function attachErrorCollector(page, errors) {
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(`[console] ${msg.text()}`); });
  page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`));
  page.on('requestfailed', (req) => errors.push(`[requestfailed] ${req.url()} ${req.failure()?.errorText}`));
}

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
  const errors = [];
  attachErrorCollector(page, errors);
  try {
    await login(page);
    const data = await seed(page);

    await page.goto(`${frontendBaseUrl}/tasks?view=tomorrow`);
    await page.getByRole('button', { name: /Zítra/ }).waitFor({ timeout: 15_000 });
    const tomorrowButton = page.getByRole('button', { name: /Zítra/ });
    await tomorrowButton.waitFor();
    if (await tomorrowButton.getAttribute('aria-pressed') !== 'true') throw new Error('Tomorrow filter is not active');
    await page.getByText(data.tomorrowTask.title).waitFor({ timeout: 15_000 });
    await page.reload();
    await page.waitForURL(/view=tomorrow/);
    if (await tomorrowButton.getAttribute('aria-pressed') !== 'true') throw new Error('Tomorrow filter did not survive reload');

    await page.goto(`${frontendBaseUrl}/dashboard`);
    const habitsSection = page.locator('section').filter({ hasText: 'Návyky dnes' });
    await habitsSection.getByText(data.challenge.title).waitFor({ timeout: 15_000 });
    const overflow = await habitsSection.locator('div').nth(1).evaluate((node) => node.scrollWidth > node.clientWidth + 2);
    if (overflow) throw new Error('Dashboard habits still overflow horizontally');
    await Promise.all([
      page.waitForResponse((response) => response.url().includes(`/challenges/${data.challenge.id}/check-in`) && response.request().method() === 'POST' && response.ok()),
      habitsSection.getByRole('button', { name: new RegExp(`Zapsat dnes: ${data.challenge.title}`) }).click(),
    ]);

    await page.goto(`${frontendBaseUrl}/inbox`);
    await page.getByLabel(`Vybrat ${data.inboxTasks[0].title}`).waitFor({ timeout: 15_000 });
    for (const task of data.inboxTasks) {
      await page.getByLabel(`Vybrat ${task.title}`).check();
    }
    await page.getByText('Vybráno 3').waitFor({ timeout: 10_000 });
    await page.getByLabel('Hromadný termín', { exact: true }).selectOption(tomorrow);
    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/tasks/') && response.request().method() === 'PATCH' && response.ok()),
      page.getByRole('button', { name: 'Použít na 3' }).click(),
    ]);
    await page.getByText('Zpracováno 3 položek.').waitFor({ timeout: 15_000 });
    let fetched = await Promise.all(data.inboxTasks.map((task) => apiJson(page, `/tasks/${task.id}`)));
    if (fetched.some((task) => task.due_date !== tomorrow)) throw new Error('Bulk due date was not applied to all selected inbox items');
    await page.getByRole('button', { name: /Vrátit/ }).click();
    await page.getByText('Vráceno 3 položek.').waitFor({ timeout: 15_000 });
    fetched = await Promise.all(data.inboxTasks.map((task) => apiJson(page, `/tasks/${task.id}`)));
    if (fetched.some((task) => task.due_date !== null)) throw new Error('Bulk undo did not restore empty due dates');

    console.log(JSON.stringify({ ok: errors.length === 0, errors, seeded: { tomorrowTask: data.tomorrowTask.id, inboxTasks: data.inboxTasks.map((task) => task.id), challenge: data.challenge.id } }, null, 2));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await run();
