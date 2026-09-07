import { chromium, request as playwrightRequest } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3000';
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';
const email = process.env.PHASE8A_E2E_EMAIL;
const password = process.env.PHASE8A_E2E_PASSWORD;
const apiKey = process.env.PHASE8A_API_KEY;

if (!email || !password || !apiKey) {
  throw new Error('Set PHASE8A_E2E_EMAIL, PHASE8A_E2E_PASSWORD and PHASE8A_API_KEY');
}

const stamp = Date.now();
const originalTitle = `Smoke agent audit ${stamp}`;
const updatedTitle = `Smoke agent audit updated ${stamp}`;
const batchId = `phase8a-smoke-${stamp}`;

async function agentMutations() {
  const api = await playwrightRequest.newContext({ baseURL: apiBaseUrl });
  const create = await api.post('/tasks', {
    headers: {
      'X-API-Key': apiKey,
      'X-Agent-Reasoning': 'Phase8A smoke creates a task through API key.',
      'X-Agent-Source': 'playwright',
      'X-Agent-Source-System': 'phase8a_smoke',
      'X-Agent-Batch-Id': batchId,
    },
    data: { title: originalTitle, priority: 'medium' },
  });
  if (create.status() !== 201) throw new Error(`API-key task create failed: ${create.status()} ${await create.text()}`);
  const task = await create.json();
  const update = await api.patch(`/tasks/${task.id}`, {
    headers: {
      'X-API-Key': apiKey,
      'X-Agent-Reasoning': 'Phase8A smoke updates task title to verify before/after diff.',
      'X-Agent-Source': 'playwright',
      'X-Agent-Source-System': 'phase8a_smoke',
      'X-Agent-Batch-Id': batchId,
      'If-Match': String(task.version),
    },
    data: { title: updatedTitle },
  });
  if (update.status() !== 200) throw new Error(`API-key task update failed: ${update.status()} ${await update.text()}`);
  await api.dispose();
  return { taskId: task.id };
}

async function login(page) {
  await page.goto(`${frontendBaseUrl}/login`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
}

async function runDesktopSmoke(browser, taskId) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 950 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (error) => errors.push(error.message));

  await login(page);
  await page.getByRole('link', { name: 'Úkoly' }).first().click();
  await page.getByRole('heading', { name: 'Úkoly' }).waitFor();
  await page.getByRole('button', { name: updatedTitle }).waitFor({ timeout: 15000 });
  const taskCard = page.locator('article', { hasText: updatedTitle }).first();
  await taskCard.getByRole('link', { name: 'Zobrazit akci agenta pro tento úkol' }).click();
  await page.getByRole('heading', { name: 'Aktivita' }).waitFor();
  await page.getByText(`Zobrazuji aktivitu pro task ${taskId}.`).waitFor();
  await page.getByRole('heading', { name: 'založil úkol' }).waitFor();

  await page.goto(`${frontendBaseUrl}/agent?action=update_task&entity_type=task&entity_id=${taskId}&only_unreverted=false`);
  await page.getByRole('heading', { name: 'upravil úkol' }).waitFor();
  await page.getByText('Porovnání před / po').click();
  await page.getByText(originalTitle).waitFor();
  await page.getByText(updatedTitle).waitFor();
  await page.getByRole('button', { name: /Vrátit/ }).last().click();
  await page.getByText('vráceno').waitFor({ timeout: 15000 });

  await page.getByRole('link', { name: 'Úkoly' }).first().click();
  await page.getByRole('button', { name: originalTitle }).waitFor({ timeout: 15000 });
  await page.screenshot({ path: '/tmp/personal-os-phase8a-desktop.png', fullPage: true });
  if (errors.length) throw new Error(`Browser console errors: ${errors.join('\n')}`);
  await page.close();
  return { desktopScreenshot: '/tmp/personal-os-phase8a-desktop.png' };
}

async function runMobileSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  await login(page);
  await page.goto(`${frontendBaseUrl}/agent`);
  await page.getByRole('heading', { name: 'Aktivita' }).waitFor();
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (!bottomVisible) throw new Error('Mobile bottom nav is not visible on agent page');
  await page.screenshot({ path: '/tmp/personal-os-phase8a-mobile.png', fullPage: true });
  await page.close();
  return { mobileScreenshot: '/tmp/personal-os-phase8a-mobile.png' };
}

const { taskId } = await agentMutations();
const browser = await chromium.launch();
try {
  const desktop = await runDesktopSmoke(browser, taskId);
  const mobile = await runMobileSmoke(browser);
  console.log(JSON.stringify({ ok: true, taskId, originalTitle, updatedTitle, batchId, ...desktop, ...mobile }, null, 2));
} finally {
  await browser.close();
}
