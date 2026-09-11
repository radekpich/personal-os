import { chromium } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3030';
const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8030';
const email = process.env.SMOKE_EMAIL;
const password = process.env.SMOKE_PASSWORD;
if (!email || !password) throw new Error('Set SMOKE_EMAIL and SMOKE_PASSWORD');

const stamp = Date.now();
const routes = ['/dashboard', '/tasks', '/inbox', '/challenges', '/diary', '/visions', '/agent', '/settings'];

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

async function seedMarkdown(page) {
  const today = new Date().toISOString().slice(0, 10);
  const category = await apiJson(page, '/categories', { method: 'POST', data: { name: `Smoke markdown kat ${stamp}`, color: '#2563EB', icon: 'check' } });
  const context = await apiJson(page, '/contexts', { method: 'POST', data: { name: `Smoke markdown kde ${stamp}`, color: '#2563EB', icon: 'pin' } });
  const task = await apiJson(page, '/tasks', {
    method: 'POST',
    data: { title: `Smoke **markdown** úkol ${stamp}`, description: '**Tučný úkol** <script>alert(1)</script>', status: 'todo', category_id: category.id, context_id: context.id },
  });
  const note = await apiJson(page, '/notes', { method: 'POST', data: { title: `Smoke markdown deník ${stamp}`, body: '**Tučný deník** <script>alert(1)</script>', kind: 'diary', entry_date: today } });
  const vision = await apiJson(page, '/visions', { method: 'POST', data: { title: `Smoke markdown vize ${stamp}`, description: '**Tučná vize** <script>alert(1)</script>', horizon: '1y' } });
  return { task, note, vision };
}

function attachErrorCollector(page, errors) {
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(`[console] ${msg.text()}`); });
  page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`));
  page.on('requestfailed', (req) => errors.push(`[requestfailed] ${req.url()} ${req.failure()?.errorText}`));
}

async function verifyBottomReachable(page, route) {
  await page.goto(`${frontendBaseUrl}${route}`);
  await page.locator('main.workspace').waitFor({ timeout: 15_000 });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => undefined);
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await page.waitForTimeout(250);
  const result = await page.evaluate(() => {
    const nav = document.querySelector('nav.bottom-nav');
    const main = document.querySelector('main.workspace');
    const lastContent = main?.lastElementChild;
    const navTop = nav?.getBoundingClientRect().top ?? window.innerHeight;
    const contentBottom = lastContent?.getBoundingClientRect().bottom ?? 0;
    const viewportBottom = window.innerHeight;
    const reachableEnd = Math.ceil(window.scrollY + viewportBottom) >= document.documentElement.scrollHeight - 2;
    return { navTop, contentBottom, viewportBottom, reachableEnd, gap: navTop - contentBottom };
  });
  if (!result.reachableEnd) throw new Error(`${route}: nejde doscrollovat na konec (${JSON.stringify(result)})`);
  if (result.contentBottom > result.navTop - 8) throw new Error(`${route}: bottom nav překrývá konec obsahu (${JSON.stringify(result)})`);
  return { route, ...result };
}

async function verifyMarkdown(page, seeded) {
  await page.goto(`${frontendBaseUrl}/tasks`);
  const taskArticle = page.locator('article').filter({ hasText: seeded.task.title }).first();
  await taskArticle.waitFor({ timeout: 15_000 });
  await taskArticle.getByText('Tučný úkol').waitFor();
  if (await taskArticle.getByText('alert(1)').isVisible().catch(() => false)) throw new Error('Markdown úkol vykreslil raw HTML obsah');

  await page.goto(`${frontendBaseUrl}/diary`);
  const noteArticle = page.locator('article').filter({ hasText: seeded.note.title }).first();
  await noteArticle.waitFor({ timeout: 15_000 });
  await noteArticle.getByText('Tučný deník').waitFor();
  if (await noteArticle.getByText('alert(1)').isVisible().catch(() => false)) throw new Error('Markdown deník vykreslil raw HTML obsah');

  await page.goto(`${frontendBaseUrl}/visions`);
  const visionCard = page.locator('article, button').filter({ hasText: seeded.vision.title }).first();
  await visionCard.waitFor({ timeout: 15_000 });
  await visionCard.getByText('Tučná vize').waitFor();
  if (await visionCard.getByText('alert(1)').isVisible().catch(() => false)) throw new Error('Markdown vize vykreslila raw HTML obsah');
  if (await page.getByText('Markdown popis zatím ukládáme jako text; render přijde později').isVisible().catch(() => false)) {
    throw new Error('Vývojářská markdown poznámka je stále vidět');
  }
}

async function verifyTaskDialogDefaults(page) {
  await page.goto(`${frontendBaseUrl}/tasks`);
  await page.getByRole('button', { name: 'Otevřít plný dialog úkolu' }).click();
  await page.getByRole('heading', { name: 'Nový úkol' }).waitFor({ timeout: 10_000 });
  const status = await page.locator('select[name="status"]').inputValue();
  if (status !== 'todo') throw new Error(`Nový úkol ze stránky Úkoly má špatný default stav: ${status}`);
  await page.getByRole('button', { name: 'Zrušit' }).click();
}

async function verifyCompletedAtDetail(page, seeded) {
  const done = await apiJson(page, `/tasks/${seeded.task.id}`, {
    method: 'PATCH',
    headers: { 'If-Match': String(seeded.task.version) },
    data: { status: 'done', completed_at: '2026-01-01T00:00:00+00:00' },
  });
  if (!done.completed_at || done.completed_by !== 'user') throw new Error(`Dokončení nevrátilo completed_at/completed_by: ${JSON.stringify(done)}`);
  if (done.completed_at.startsWith('2026-01-01')) throw new Error('Backend převzal klientský completed_at místo serverového času');
  await page.goto(`${frontendBaseUrl}/tasks?status=done`);
  const article = page.locator('article').filter({ hasText: seeded.task.title }).first();
  await article.waitFor({ timeout: 15_000 });
  await article.getByRole('button', { name: 'Otevřít detail' }).click();
  await page.getByText(/Splněno /).waitFor({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Zrušit' }).click();
}

async function verifyRecurrencePanel(page) {
  await page.goto(`${frontendBaseUrl}/tasks`);
  await page.getByRole('button', { name: 'Otevřít plný dialog úkolu' }).click();
  await page.getByRole('heading', { name: 'Nový úkol' }).waitFor({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Zapnout' }).click();
  await page.getByRole('button', { name: 'Vlastní nastavení' }).click();
  await page.getByText('Nastavení teď znamená').waitFor();
  await page.locator('select').filter({ hasText: 'Týdně' }).selectOption('weekly');
  await page.getByRole('button', { name: 'St', exact: true }).click();
  await page.getByText(/Každé .*středu|Každé .*pondělí/).waitFor();
  await page.getByRole('radio', { name: 'Do data' }).check();
  await page.locator('input[type="date"]').last().fill('2026-12-31');
  await page.getByText(/do 31\. prosince 2026/).waitFor();
  if (!(await page.getByRole('button', { name: 'Potvrdit' }).isVisible())) throw new Error('Chybí tlačítko Potvrdit');
  await page.getByRole('button', { name: 'Zrušit' }).first().click();
  if (await page.getByText('Nastavení teď znamená').isVisible().catch(() => false)) throw new Error('Zrušit nesbalilo panel');
  await page.getByRole('button', { name: 'Zrušit' }).click();
}

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 900 }, isMobile: true });
  const errors = [];
  attachErrorCollector(page, errors);
  try {
    await login(page);
    const seeded = await seedMarkdown(page);
    await verifyMarkdown(page, seeded);
    await verifyTaskDialogDefaults(page);
    await verifyCompletedAtDetail(page, seeded);
    await verifyRecurrencePanel(page);
    const scroll = [];
    for (const route of routes) scroll.push(await verifyBottomReachable(page, route));
    await page.screenshot({ path: '/tmp/personal-os-mobile-bottom-smoke.png', fullPage: true });
    console.log(JSON.stringify({ ok: errors.length === 0, errors, scroll }, null, 2));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await run();
