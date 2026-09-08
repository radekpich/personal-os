import { chromium, request as playwrightRequest } from '@playwright/test';

const frontendBaseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:3000';
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';
const email = process.env.PHASE8B_E2E_EMAIL;
const password = process.env.PHASE8B_E2E_PASSWORD;
const apiKey = process.env.PHASE8B_API_KEY;

if (!email || !password || !apiKey) {
  throw new Error('Set PHASE8B_E2E_EMAIL, PHASE8B_E2E_PASSWORD and PHASE8B_API_KEY');
}

const stamp = Date.now();
const jobName = `Phase8B Smoke Job ${stamp}`;
const integrationName = `Phase8B Gmail ${stamp}`;
const watchName = `Phase8B Disk ${stamp}`;
const runSummary = `Phase8B smoke run ${stamp}`;
const channelIdentifier = `Phase8B Home ${stamp}`;
const snapshotHash = `phase8b-smoke-${stamp}`;

async function reportRegistryAndRun() {
  const api = await playwrightRequest.newContext({ baseURL: apiBaseUrl });
  const snapshot = {
    agent: {
      name: 'hermes-phase8b-smoke',
      version: 'smoke',
      host: 'playwright',
      status: 'running',
      started_at: new Date().toISOString(),
    },
    snapshot_hash: snapshotHash,
    jobs: [
      {
        name: jobName,
        description: 'Smoke scheduled job',
        schedule: '*/5 * * * *',
        schedule_description: 'každých 5 minut',
        is_enabled: true,
        next_run_at: new Date(Date.now() + 300_000).toISOString(),
        last_status: 'success',
        consecutive_failures: 0,
        run_count: 1,
        tags: ['smoke', 'phase8b'],
      },
    ],
    integrations: [
      {
        name: integrationName,
        kind: 'email',
        scopes: ['gmail.readonly', 'gmail.send'],
        status: 'active',
        error_count: 0,
        notes: 'Smoke metadata only; no token stored',
      },
    ],
    watches: [
      {
        name: watchName,
        description: 'Smoke disk watcher',
        kind: 'threshold',
        config_json: { metric: 'disk_percent', threshold: 85 },
        schedule: '*/30 * * * *',
        is_active: true,
        last_result: 'ok',
      },
    ],
    channels: [
      {
        channel_type: 'telegram',
        identifier: channelIdentifier,
        is_active: true,
        message_count_24h: 2,
        message_count_month: 8,
      },
    ],
    capabilities: [
      {
        name: `phase8b-capability-${stamp}`,
        description: 'Smoke capability',
        is_enabled: true,
        metadata_json: { smoke: true },
      },
    ],
  };

  const firstSync = await api.post('/agent/registry/sync', {
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    data: snapshot,
  });
  if (firstSync.status() !== 200) throw new Error(`registry sync failed: ${firstSync.status()} ${await firstSync.text()}`);
  const firstSyncJson = await firstSync.json();
  if (firstSyncJson.idempotent || firstSyncJson.changes_created < 5) throw new Error(`unexpected first sync response: ${JSON.stringify(firstSyncJson)}`);

  const secondSync = await api.post('/agent/registry/sync', {
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    data: snapshot,
  });
  if (secondSync.status() !== 200) throw new Error(`idempotent registry sync failed: ${secondSync.status()} ${await secondSync.text()}`);
  const secondSyncJson = await secondSync.json();
  if (!secondSyncJson.idempotent || secondSyncJson.changes_created !== 0) throw new Error(`registry sync was not idempotent: ${JSON.stringify(secondSyncJson)}`);

  const run = await api.post('/agent/runs', {
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    data: {
      agent: { name: 'hermes-phase8b-smoke', host: 'playwright', status: 'running' },
      runs: [
        {
          trigger: 'schedule',
          job_name: jobName,
          summary: runSummary,
          detail: 'Smoke run visible in Historie tab.',
          status: 'success',
          started_at: new Date().toISOString(),
          finished_at: new Date().toISOString(),
          duration_ms: 123,
          tokens_used: 321,
          cost_estimate: 0.01,
          tags: ['smoke', 'phase8b'],
        },
      ],
    },
  });
  if (run.status() !== 200) throw new Error(`run report failed: ${run.status()} ${await run.text()}`);
  await api.dispose();
}

async function expectReportedKeyRevoked() {
  const api = await playwrightRequest.newContext({ baseURL: apiBaseUrl });
  const response = await api.post('/agent/runs', {
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    data: { runs: [] },
  });
  const status = response.status();
  await api.dispose();
  if (status !== 401) throw new Error(`expected revoked report key to fail with 401, got ${status}`);
}

async function login(page) {
  await page.goto(`${frontendBaseUrl}/login`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Heslo').fill(password);
  await page.getByRole('button', { name: 'Přihlásit' }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor();
}

async function clickTab(page, name) {
  await page.getByRole('button', { name }).click();
}

async function runDesktopSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 950 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (error) => errors.push(error.message));

  await login(page);
  await page.goto(`${frontendBaseUrl}/agent`);
  await page.getByRole('button', { name: 'Přehled' }).waitFor();
  await page.getByText('Nepotvrzené změny konfigurace:').waitFor({ timeout: 15_000 });
  await page.getByText(channelIdentifier, { exact: true }).first().waitFor();

  await clickTab(page, 'Úlohy');
  await page.getByText(jobName).first().waitFor();
  await clickTab(page, 'Přístupy');
  await page.getByText(integrationName).waitFor();
  await page.getByText('zápisový přístup').waitFor();
  await clickTab(page, 'Hlídání');
  await page.getByText(watchName).waitFor();
  await clickTab(page, 'Historie');
  await page.getByText(runSummary).waitFor();
  await clickTab(page, 'Změny');
  await page.getByText(jobName).first().waitFor();
  const ackButton = page.getByRole('button', { name: 'Potvrdit' }).first();
  if (await ackButton.isVisible()) await ackButton.click();
  await clickTab(page, 'Klíče');
  await page.getByText('Nouzové odebrání přístupu').waitFor();
  await page.getByText('phase8b-report').waitFor();
  page.once('dialog', async (dialog) => { await dialog.accept(); });
  await page.getByRole('button', { name: 'Zneplatnit všechny agentní klíče' }).click();
  await page.screenshot({ path: '/tmp/personal-os-phase8b-desktop.png', fullPage: true });
  if (errors.length) throw new Error(`Browser console errors: ${errors.join('\n')}`);
  await page.close();
  return { desktopScreenshot: '/tmp/personal-os-phase8b-desktop.png' };
}

async function runMobileSmoke(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  await login(page);
  await page.goto(`${frontendBaseUrl}/agent`);
  await page.getByRole('button', { name: 'Přehled' }).waitFor();
  const bottomVisible = await page.locator('.bottom-nav').isVisible();
  if (!bottomVisible) throw new Error('Mobile bottom nav is not visible on agent page');
  await page.screenshot({ path: '/tmp/personal-os-phase8b-mobile.png', fullPage: true });
  await page.close();
  return { mobileScreenshot: '/tmp/personal-os-phase8b-mobile.png' };
}

await reportRegistryAndRun();
const browser = await chromium.launch();
try {
  const desktop = await runDesktopSmoke(browser);
  await expectReportedKeyRevoked();
  const mobile = await runMobileSmoke(browser);
  console.log(JSON.stringify({ ok: true, jobName, integrationName, watchName, runSummary, snapshotHash, ...desktop, ...mobile }, null, 2));
} finally {
  await browser.close();
}
