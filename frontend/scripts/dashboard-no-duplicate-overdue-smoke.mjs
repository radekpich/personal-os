import { chromium, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const credentials = Object.fromEntries(readFileSync('/home/zeus/personal-os-preview/radek-login.txt', 'utf8').trim().split('\n').map(line => { const i = line.indexOf('='); return [line.slice(0,i),line.slice(i+1)]; }));
const base = process.env.FRONTEND_BASE_URL ?? 'http://38.79.154.155:3030';
const browser = await chromium.launch({headless:true});
const errors = [];
try {
 for (const viewport of [{width:1650,height:900},{width:390,height:844}]) {
  const page = await browser.newPage({viewport});
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`${base}/login`);
  await page.locator('input[type=email]').fill(credentials.email);
  await page.locator('input[type=password]').fill(credentials.password);
  await page.getByRole('button',{name:'Přihlásit'}).click();
  await expect(page.getByRole('heading',{name:'Přehled',exact:true})).toBeVisible();
  await expect(page.locator('main a[href="/tasks?view=overdue"]')).toHaveCount(1);
  await expect(page.locator('main').getByText(/^Po termínu:/)).toHaveCount(0);
  await page.locator('main a[href="/tasks?view=overdue"]').click();
  await expect(page).toHaveURL(/view=overdue/);
  await page.close();
 }
 expect(errors).toEqual([]);
 console.log(JSON.stringify({ok:true,viewports:['desktop','mobile'],errors}));
} finally {await browser.close();}
