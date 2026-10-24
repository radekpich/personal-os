import { chromium, expect, devices, request } from '@playwright/test';
const frontend = process.env.FRONTEND_BASE_URL ?? 'http://38.79.154.155:3030';
const backend = process.env.CATEGORY_SMOKE_BACKEND ?? 'http://127.0.0.1:8031';
if (!['127.0.0.1', 'localhost'].includes(new URL(backend).hostname)) throw new Error('Seed only an isolated local backend');
const api = await request.newContext({ baseURL: backend });
async function call(path, data) {
  const state = await api.storageState();
  const csrf = state.cookies.find(c => c.name === 'csrf_token')?.value ?? '';
  const r = data === undefined ? await api.get(path) : await api.post(path, { data: ['/categories', '/contexts'].includes(path) ? { color: '#d49c55', icon: 'folder', ...data } : data, headers: { 'X-CSRF-Token': csrf } });
  expect(r.ok(), `${path}: ${await r.text()}`).toBeTruthy();
  return r.json();
}
await call('/health');
await call('/auth/login', { email: 'calendar-smoke@example.test', password: 'Calendar-smoke-only-2026' });
const stamp = Date.now();
const category = await call('/categories', { name: 'Kategorie klik ' + stamp });
const other = await call('/categories', { name: 'Jiná kategorie ' + stamp });
const context = await call('/contexts', { name: 'Místo klik ' + stamp });
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Prague' }).format(new Date());
const next = new Date(today + 'T12:00:00Z'); next.setUTCDate(next.getUTCDate() + 3);
const title = 'Klik kategorie ' + stamp;
await call('/tasks', { title, category_id: category.id, context_id: context.id, due_date: today, status: 'todo', priority: 'high' });
await call('/tasks', { title: 'Další termín ' + stamp, category_id: category.id, due_date: next.toISOString().slice(0,10), status: 'blocked', priority: 'low' });
await call('/tasks', { title: 'Hotový ' + stamp, category_id: category.id, due_date: today, status: 'done', priority: 'high' });
await call('/tasks', { title: 'Jiný ' + stamp, category_id: other.id, due_date: today, status: 'todo' });
const browser = await chromium.launch(); const errors = []; const results = []; let activePage;
try {
  for (const [index, device] of [{ viewport: { width: 1440, height: 900 } }, devices['Pixel 5']].entries()) {
    const ctx = await browser.newContext(device); const page = await ctx.newPage(); activePage = page;
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.route('http://38.79.154.155:8030/**', async route => { const u = new URL(route.request().url()); await route.fulfill({ response: await route.fetch({ url: backend + u.pathname + u.search }) }); });
    await page.goto(frontend + '/login'); await page.locator('input[type=email]').fill('calendar-smoke@example.test'); await page.locator('input[type=password]').fill('Calendar-smoke-only-2026'); await page.getByRole('button', { name: 'Přihlásit' }).click(); await expect(page.getByRole('heading', { name: 'Přehled', exact: true })).toBeVisible();
    await page.goto(frontend + '/tasks?' + new URLSearchParams({ view: 'today', priority: 'high', q: title, context_id: context.id }));
    const card = page.locator('article').filter({ has: page.getByRole('button', { name: title, exact: true }) }); await expect(card).toBeVisible();
    await expect(card.getByRole('link', { name: 'Zobrazit úkoly v kategorii ' + category.name, exact: true })).toBeVisible();
    const listResponse = page.waitForResponse(r => { const u = new URL(r.url()); return u.port === '8030' && u.pathname === '/tasks' && u.searchParams.get('category_id') === category.id && u.searchParams.get('page_size') === '50' && !u.searchParams.has('view'); });
    await card.getByRole('link', { name: 'Zobrazit úkoly v kategorii ' + category.name, exact: true }).click();
    await expect(page).toHaveURL(frontend + '/tasks?category_id=' + category.id);
    const response = await listResponse; expect(response.ok()).toBeTruthy(); const data = await response.json(); expect(data.total).toBe(2); expect(data.items.every(t => t.category_id === category.id && !['done','cancelled'].includes(t.status))).toBeTruthy();
    await expect(page.locator('article.task-row')).toHaveCount(2); await expect(page.getByRole('dialog')).toHaveCount(0);
    const clear = page.getByRole('button', { name: 'Zrušit filtr kategorie ' + category.name, exact: true }); await expect(clear).toBeVisible();
    await page.reload(); await expect(clear).toBeVisible(); await expect(page.locator('article.task-row')).toHaveCount(2);
    const clearedResponse = page.waitForResponse(r => { const u = new URL(r.url()); return u.port === '8030' && u.pathname === '/tasks' && u.searchParams.get('page_size') === '50' && !u.searchParams.has('category_id') && !u.searchParams.has('q'); });
    await clear.click(); await expect(page).toHaveURL(frontend + '/tasks'); const cleared = await (await clearedResponse).json(); expect(cleared.total).toBeGreaterThan(2); await expect(page.locator('article.task-row')).toHaveCount(cleared.items.length); await expect(clear).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth && document.body.scrollWidth <= document.body.clientWidth)).toBeTruthy();
    results.push({ device: index, cleanCategoryUrl: true, allOpenCategoryTasks: 2, reloadPersists: true, clearWorks: true }); await ctx.close();
  }
  expect(errors).toEqual([]); console.log(JSON.stringify({ ok: true, isolatedBackend: backend, results, errors }));
} catch (error) { if (activePage) console.error(await activePage.locator('body').ariaSnapshot()); throw error; }
finally { await browser.close(); await api.dispose(); }
