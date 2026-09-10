import { chromium } from '@playwright/test';

const base = process.env.FRONTEND_BASE_URL ?? 'http://38.79.154.155:3030';
const email = process.env.SMOKE_EMAIL ?? 'radek-preview@example.com';
const password = process.env.SMOKE_PASSWORD ?? 'correct-password';
const errors = [];

async function visibleText(page, text) {
  return await page.getByText(text, { exact: false }).first().isVisible().catch(() => false);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
try {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Email').fill(email);
  await page.getByLabel(/Heslo/i).fill(password);
  await page.getByRole('button', { name: /Přihlásit/i }).click();
  await page.getByRole('heading', { name: 'Přehled' }).waitFor({ timeout: 15000 });

  await page.goto(`${base}/tasks`, { waitUntil: 'networkidle' });
  await page.getByLabel('Otevřít plný dialog úkolu').click();
  await page.getByText('Opakování', { exact: true }).waitFor();
  if (await visibleText(page, 'FREQ=WEEKLY')) errors.push('Task dialog still exposes RRULE placeholder');
  if (await visibleText(page, 'Typ opakování')) errors.push('Task recurrence type visible before recurrence enabled');
  await page.getByRole('button', { name: /Zapnout/i }).click();
  await page.getByRole('button', { name: /3× týdně/i }).click();
  await page.getByText(/Každé pondělí, středu a pátek/i).waitFor();
  await page.getByText('Typ opakování').waitFor();
  await page.getByText('Podle rozvrhu').waitFor();
  await page.getByText('Po dokončení').waitFor();
  if (await visibleText(page, 'fixed')) errors.push('Task recurrence type exposes fixed');
  if (await visibleText(page, 'after_completion')) errors.push('Task recurrence type exposes after_completion');
  await page.keyboard.press('Escape');

  await page.goto(`${base}/challenges`, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /Nová výzva/i }).click();
  await page.getByText('Rozvrh výzvy').waitFor();
  await page.getByText('Každý den').waitFor();
  await page.getByRole('button', { name: /3× týdně/i }).click();
  await page.getByText(/Každé pondělí, středu a pátek/i).waitFor();
  await page.getByText('Povolené vynechání').waitFor();
  await page.getByText(/Kolik dní z rozvrhu smím vynechat/i).waitFor();
  if (await visibleText(page, 'Grace dny')) errors.push('Challenge dialog still says Grace dny');
  if (await visibleText(page, 'FREQ=WEEKLY')) errors.push('Challenge dialog exposes RRULE string');
  await page.keyboard.press('Escape');

  const heatmap = page.getByLabel('Heatmapa návyků podle rozvrhu');
  await heatmap.getByText('Po', { exact: true }).waitFor({ timeout: 10000 });
  await heatmap.getByText('St', { exact: true }).waitFor({ timeout: 10000 });
  await heatmap.getByText('Pá', { exact: true }).waitFor({ timeout: 10000 });
  const heatCell = heatmap.locator('[title*="v rozvrhu"], [title*="mimo rozvrh"]').first();
  await heatCell.waitFor({ timeout: 10000 });
  const title = await heatCell.getAttribute('title');
  if (!title || !/(v rozvrhu|mimo rozvrh)/.test(title)) errors.push('Heatmap tooltip does not describe schedule state');

  await page.screenshot({ path: '/tmp/personal-os-batch3-recurrence-smoke.png', fullPage: true });
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
} finally {
  await browser.close();
}
console.log(JSON.stringify({ ok: errors.length === 0, errors }, null, 2));
process.exit(errors.length ? 1 : 0);
