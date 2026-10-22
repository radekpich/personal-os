import { chromium, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const credentials = Object.fromEntries(readFileSync('/home/zeus/personal-os-preview/radek-login.txt', 'utf8').trim().split('\n').map(l => {const i=l.indexOf('='); return [l.slice(0,i),l.slice(i+1)];}));
const base=process.env.FRONTEND_BASE_URL ?? 'http://38.79.154.155:3030';
const browser=await chromium.launch();const errors=[];const results=[];
try {
 for(const viewport of [{width:1650,height:900},{width:390,height:844}]) {
  const page=await browser.newPage({viewport});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/login');await page.locator('input[type=email]').fill(credentials.email);await page.locator('input[type=password]').fill(credentials.password);await page.getByRole('button',{name:'Přihlásit'}).click();await expect(page.getByRole('heading',{name:'Přehled',exact:true})).toBeVisible();
  const pending=page.waitForResponse(r=>{const u=new URL(r.url());return u.port==='8030'&&u.pathname==='/tasks'&&!u.searchParams.has('view')&&!u.searchParams.has('status')&&r.request().method()==='GET';});
  await page.goto(base+'/tasks');const response=await pending;expect(response.ok()).toBeTruthy();const data=await response.json();expect(data.items.every(t=>!['done','cancelled'].includes(t.status))).toBeTruthy();
  const done=page.waitForResponse(r=>{const u=new URL(r.url());return u.port==='8030'&&u.pathname==='/tasks'&&u.searchParams.get('status')==='done'&&r.request().method()==='GET';});
  await page.goto(base+'/tasks?status=done');const closed=await done;expect(closed.ok()).toBeTruthy();const completed=await closed.json();expect(completed.items.every(t=>t.status==='done')).toBeTruthy();
  results.push({width:viewport.width,open:data.total,completed:completed.total});await page.close();
 }
 expect(errors).toEqual([]);console.log(JSON.stringify({ok:true,results,errors}));
}finally{await browser.close();}
