import {chromium, expect, devices} from '@playwright/test';
const base=process.env.FRONTEND_BASE_URL??'http://38.79.154.155:3030';
const isolated=process.env.CALENDAR_SMOKE_BACKEND??'http://127.0.0.1:8031';
const browser=await chromium.launch();const errors=[];const results=[];
try{
 for(const [index,device] of [{viewport:{width:1440,height:900}},devices['Pixel 5']].entries()){
  const context=await browser.newContext(device);const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://38.79.154.155:8030/**',async route=>{
   const u=new URL(route.request().url());const response=await route.fetch({url:isolated+u.pathname+u.search});await route.fulfill({response});
  });
  await page.goto(base+'/login');await page.locator('input[type=email]').fill('calendar-smoke@example.test');await page.locator('input[type=password]').fill('Calendar-smoke-only-2026');await page.getByRole('button',{name:'Přihlásit'}).click();await expect(page.getByRole('heading',{name:'Přehled',exact:true})).toBeVisible();
  async function api(path,method='GET',body){return page.evaluate(async({path,method,body})=>{
   const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrf_token='))?.split('=').slice(1).join('=')??'';
   const response=await fetch('http://38.79.154.155:8030'+path,{method,credentials:'include',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(body?{body:JSON.stringify(body)}:{})});if(!response.ok)throw new Error(await response.text());return response.json();
  },{path,method,body});}
  const category=(await api('/categories')).items[0].id;
  for(const dated of [true,false]){
   const task=await api('/tasks','POST',{title:`Calendar E2E ${index} ${dated} ${Date.now()}`,category_id:category,status:'todo',...(dated?{due_date:'2027-02-10',due_time:'10:30:00',estimate_minutes:60}:{})});
   await page.goto(base+'/tasks');const card=page.locator('article').filter({has:page.getByRole('button',{name:task.title,exact:true})});await card.getByRole('button',{name:'Zapsat do Google Kalendáře',exact:true}).click();
   const dialog=page.getByRole('dialog',{name:'Zapsat do kalendáře',exact:true});await expect(dialog).toBeVisible();await expect(dialog.getByLabel('Datum',{exact:true})).toHaveValue(dated?'2027-02-10':'');await expect(dialog.getByLabel('Čas',{exact:true})).toHaveValue(dated?'10:30':'09:00');
   expect(await dialog.evaluate(el=>!el.closest('article'))).toBeTruthy();await expect(dialog.getByRole('button',{name:'Zadat požadavek'})).toBeInViewport();
   if(!dated){await dialog.getByRole('button',{name:'Zadat požadavek'}).click();await expect(dialog).toBeVisible();await expect(dialog.getByText('Bez data nejde požadavek odeslat.')).toBeVisible();const unchanged=await api('/tasks/'+task.id);expect(unchanged.due_date).toBeNull();}
   await dialog.getByLabel('Datum',{exact:true}).fill('2027-02-12');await dialog.getByLabel('Čas',{exact:true}).fill('14:45');
   const submitted=page.waitForResponse(r=>r.url().endsWith('/tasks/'+task.id+'/calendar-request')&&r.request().method()==='POST');await dialog.getByRole('button',{name:'Zadat požadavek'}).click();const response=await submitted;expect(response.status()).toBe(201);const request=await response.json();expect(request.starts_at).toContain('2027-02-12T14:45:00');await expect(dialog).toHaveCount(0);
   const updated=await api('/tasks/'+task.id);expect(updated.due_date).toBe('2027-02-12');expect(updated.due_time).toBe('14:45:00');expect(updated.estimate_minutes).toBe(dated?60:30);expect(updated.version).toBe(task.version+1);
   await page.goto(base+'/inbox');await page.goto(base+'/tasks');await page.locator('article').filter({has:page.getByRole('button',{name:task.title,exact:true})}).getByRole('button',{name:'Zapsat do Google Kalendáře',exact:true}).click();await expect(dialog.getByLabel('Datum',{exact:true})).toHaveValue('2027-02-12');await expect(dialog.getByLabel('Čas',{exact:true})).toHaveValue('14:45');await dialog.getByRole('button',{name:'Zavřít',exact:true}).click();
   results.push({device:index,dated,saved:true});
  }
  await context.close();
 }
 expect(errors).toEqual([]);console.log(JSON.stringify({ok:true,isolatedBackend:isolated,results,errors,noGoogleWrites:true}));
}finally{await browser.close();}
