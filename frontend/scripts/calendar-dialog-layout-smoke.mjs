import {chromium, expect, devices} from '@playwright/test';
import {readFileSync} from 'node:fs';
const c=Object.fromEntries(readFileSync('/home/zeus/personal-os-preview/radek-login.txt','utf8').trim().split('\n').map(l=>{const i=l.indexOf('=');return[l.slice(0,i),l.slice(i+1)];}));
const browser=await chromium.launch();
try{
 for(const device of [{viewport:{width:1440,height:900}},devices['Pixel 5']]){
  const context=await browser.newContext(device);const page=await context.newPage();
  await page.goto('http://38.79.154.155:3030/login');await page.locator('input[type=email]').fill(c.email);await page.locator('input[type=password]').fill(c.password);await page.getByRole('button',{name:'Přihlásit'}).click();await expect(page.getByRole('heading',{name:'Přehled',exact:true})).toBeVisible();
  const response=await context.request.get('http://38.79.154.155:8030/tasks?page_size=100');expect(response.ok()).toBeTruthy();const tasks=(await response.json()).items;await page.goto('http://38.79.154.155:3030/tasks');const task=tasks.find(t=>!t.due_time)??tasks[0];expect(task).toBeTruthy();
  await page.route('**/tasks/*/calendar-request',route=>route.abort());
  const card=page.locator('article').filter({has:page.getByRole('button',{name:task.title,exact:true})});await card.getByRole('button',{name:'Zapsat do Google Kalendáře',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Zapsat do kalendáře',exact:true});await expect(dialog).toBeVisible();await expect(dialog.getByLabel('Datum',{exact:true})).toHaveValue(task.due_date??'');
  await expect(dialog.getByRole('button',{name:'Zadat požadavek'})).toBeInViewport();expect(await dialog.evaluate(el=>!el.closest('article'))).toBeTruthy();
  await dialog.getByRole('button',{name:'Zavřít',exact:true}).click();await expect(dialog).toHaveCount(0);await context.close();
 }
 console.log(JSON.stringify({ok:true,desktop:true,mobile:true}));
}finally{await browser.close();}
