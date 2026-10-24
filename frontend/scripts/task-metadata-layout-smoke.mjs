import {chromium,expect,devices,request} from '@playwright/test';
const frontend=process.env.FRONTEND_BASE_URL??'http://38.79.154.155:3030';
const backend=process.env.TASK_METADATA_SMOKE_BACKEND??'http://127.0.0.1:8031';
if(!['127.0.0.1','localhost'].includes(new URL(backend).hostname)) throw new Error('Only an isolated local DB may be seeded');
const api=await request.newContext({baseURL:backend});
async function call(path,data){const state=await api.storageState();const csrf=state.cookies.find(c=>c.name==='csrf_token')?.value??'';const r=data===undefined?await api.get(path):await api.post(path,{data,headers:{'X-CSRF-Token':csrf}});expect(r.ok(),`${path}: ${await r.text()}`).toBeTruthy();return r.json();}
await call('/health');await call('/auth/login',{email:'calendar-smoke@example.test',password:'Calendar-smoke-only-2026'});
const stamp=Date.now(),prefix='Metadata '+stamp;
const category=await call('/categories',{name:'Stavba '+stamp,color:'#d49c55',icon:'home'});
const context=await call('/contexts',{name:'Místo '+stamp,color:'#d49c55',icon:'home'});
const tag=await call('/tags',{name:'Detail '+stamp,color:'#d49c55'});
const titles=[prefix+' A – delší název stavebního úkolu, který se na telefonu zalomí',prefix+' B',prefix+' C'];
await call('/tasks',{title:titles[0],category_id:category.id,priority:'medium',due_date:'2026-01-15',description:'Delší popis úkolu. '.repeat(12),status:'todo'});
await call('/tasks',{title:titles[1],priority:'none',status:'todo'});
await call('/tasks',{title:titles[2],category_id:category.id,priority:'high',context_id:context.id,tag_ids:[tag.id],status:'todo'});
await call('/tasks',{title:prefix+' Hotový',category_id:category.id,priority:'medium',due_date:'2026-01-15',status:'done'});
const browser=await chromium.launch(),errors=[],results=[];let activePage;
try{
 for(const [index,device] of [{viewport:{width:1440,height:1000}},{...devices['Pixel 5'],viewport:{width:375,height:812}}].entries()){
  const c=await browser.newContext({...device,colorScheme:index===1?'dark':'light'}),page=await c.newPage();activePage=page;page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.route('http://38.79.154.155:8030/**',async route=>{const u=new URL(route.request().url());await route.fulfill({response:await route.fetch({url:backend+u.pathname+u.search})});});
  await page.goto(frontend+'/login');await page.locator('input[type=email]').fill('calendar-smoke@example.test');await page.locator('input[type=password]').fill('Calendar-smoke-only-2026');await page.getByRole('button',{name:'Přihlásit'}).click();await expect(page.getByRole('heading',{name:'Přehled',exact:true})).toBeVisible();await page.goto(frontend+'/tasks?status=todo&q='+encodeURIComponent(prefix));await expect(page.locator('article.task-row')).toHaveCount(3);
  const geometry=[];
  for(const title of titles){const card=page.locator('article').filter({has:page.getByRole('button',{name:title,exact:true})});const details=card.locator('dl[aria-label="Podrobnosti úkolu"]');await expect(details).toBeVisible();await expect(details.locator('dt')).toHaveText(['Kategorie','Priorita','Termín','Stav']);expect(await details.locator(':scope > div').count()).toBe(4);geometry.push(await details.locator('dd').evaluateAll(els=>els.map(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height};})));}
  for(const g of geometry){expect(Math.max(...g.map(v=>v.height))).toBeLessThanOrEqual(30);expect(Math.max(...g.map(v=>v.y))-Math.min(...g.map(v=>v.y))).toBeLessThanOrEqual(1);for(let i=0;i<4;i++){expect(Math.abs(g[i].x-geometry[0][i].x)).toBeLessThanOrEqual(1);expect(Math.abs(g[i].width-geometry[0][i].width)).toBeLessThanOrEqual(1);}}
  const empty=page.locator('article').filter({has:page.getByRole('button',{name:titles[1],exact:true})});await expect(empty.locator('dd')).toHaveText(['—','—','—','Čeká']);const first=page.locator('article').filter({has:page.getByRole('button',{name:titles[0],exact:true})});await expect(first.locator('dd').nth(2)).toHaveText('15.1.2026');
  await page.screenshot({path:`/tmp/task-metadata-${index}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth&&document.body.scrollWidth<=document.body.clientWidth)).toBeTruthy();
  await first.getByRole('button',{name:'Upravit úkol',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await first.getByRole('link',{name:'Zobrazit úkoly v kategorii '+category.name,exact:true}).click();await expect(page).toHaveURL(frontend+'/tasks?category_id='+category.id);await expect(page.locator('article.task-row')).toHaveCount(2);
  await page.goto(frontend+'/tasks?status=done&q='+encodeURIComponent(prefix));await expect(page.locator('article.task-row')).toHaveCount(1);const completed=page.locator('article.task-row');await expect(completed.locator('dt')).toHaveText(['Kategorie','Priorita','Termín','Stav']);await expect(completed.locator('dd').nth(3)).toHaveText('Hotovo');await expect(completed.getByText('agent',{exact:true})).toHaveCount(0);await expect(completed.getByRole('button',{name:'Vrátit úkol',exact:true})).toBeVisible();await page.screenshot({path:`/tmp/task-status-${index}.png`,fullPage:true});
  results.push({device:index,alignedColumns:true,emptyPlaceholders:true,compactDate:true,editAndCategoryLink:true,completedStatusInRow:true,noOriginBadge:true});await c.close();
 }
 expect(errors).toEqual([]);console.log(JSON.stringify({ok:true,isolatedBackend:backend,results,errors}));
}catch(error){if(activePage)console.error(await activePage.locator('body').ariaSnapshot());throw error;}finally{await browser.close();await api.dispose();}
