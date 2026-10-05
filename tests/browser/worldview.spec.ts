import { test, expect } from '@playwright/test';
import fs from 'node:fs';
test.beforeEach(async({page})=>{await page.route('**/data/manifest.json',r=>r.fulfill({contentType:'application/json',body:fs.readFileSync('public/data/demo-manifest.json','utf8')}));});
test('country city, evidence, filters, comparison and replay work',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'The internet, from here.'})).toBeVisible();
  await expect(page.getByText('Synthetic demonstration · illustrative topics and arrivals')).toBeVisible();
  await page.getByRole('button',{name:'List view',exact:true}).click();
  await expect(page.locator('.topic-card')).not.toHaveCount(0);
  await page.getByRole('button',{name:'Look through the AI lens'}).click();
  await expect(page.locator('.topic-card').first().locator('.topic-category')).toHaveText('ai');
  await page.locator('#country').selectOption('JP');
  await expect(page.locator('.city-heading h2')).toContainText('Japan');
  await page.getByRole('button',{name:'Compare viewpoints'}).click();
  await expect(page.getByText('topic overlap', {exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Close comparison'}).click();
  await page.getByRole('button',{name:'English control',exact:true}).click();
  await page.getByRole('button',{name:'Next snapshot'}).click();
  await expect(page.locator('.frame-count')).toContainText('02');
  await page.getByRole('button',{name:'About this recording'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  expect(errors).toEqual([]);
});
test('mobile provides a useful accessible list fallback',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  await page.getByRole('button',{name:'List view',exact:true}).click();
  await expect(page.locator('.topic-card').first()).toBeVisible();
  await page.getByRole('button',{name:'Look through the AI lens'}).click();
  await expect(page.locator('.topic-card').first()).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  expect(overflow).toBe(false);
});
test('missing public data offers a clearly labeled demonstration',async({page})=>{
  await page.route('**/data/manifest.json',r=>r.fulfill({status:404,body:'Not found'}));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore demonstration'}).click();
  await expect(page.getByText('Synthetic demonstration · illustrative topics and arrivals')).toBeVisible();
});

test('published pilot opens real evidence and reconciles visitors',async({page})=>{
  await page.unroute('**/data/manifest.json');
  await page.emulateMedia({reducedMotion:'reduce'});
  const manifest=JSON.parse(fs.readFileSync('public/data/manifest.json','utf8'));
  const recording=JSON.parse(fs.readFileSync('public'+manifest.recordingUrl,'utf8'));
  const snapshot=recording.snapshots.find((s:any)=>s.country==='SG'&&s.profile==='local'&&s.window===recording.windows.at(-1));
  const universe=new Map<string,any>();for(const s of recording.snapshots.filter((s:any)=>s.country==='SG'&&s.profile==='local'))for(const t of s.topics)if(!universe.has(t.id))universe.set(t.id,t);
  const ids=new Set([...universe.values()].sort((a,b)=>b.count-a.count||a.id.localeCompare(b.id)).slice(0,48).map(t=>t.id));
  const count=snapshot.topics.filter((t:any)=>ids.has(t.id)).reduce((n:number,t:any)=>n+t.items.length,0);
  await page.goto('/');
  await expect(page.getByText('RECORDED OBSERVATIONS',{exact:true})).toBeVisible();
  await expect(page.locator('[data-resident-count]')).toHaveAttribute('data-resident-count',String(count),{timeout:30000});
  if(recording.windows.length<2)await expect(page.getByRole('button',{name:'Play replay'})).toBeDisabled();else await expect(page.getByRole('button',{name:'Play replay'})).toBeEnabled();
  await page.getByRole('button',{name:'List view',exact:true}).click();
  await expect(page.locator('.topic-card')).toHaveCount(snapshot.topics.length);
  await expect(page.locator('.evidence-item a').first()).toHaveAttribute('href',/^https:\/\//);
  await page.locator('#country').selectOption('DE');
  await page.getByRole('button',{name:'English control',exact:true}).click();
  await expect(page.getByText('No observations in this view',{exact:false})).toBeVisible();
});

test('shop focus has a clear exit and trends keep a topic across country navigation',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.locator('[data-focused-topic]').waitFor({timeout:30000});
 await page.locator('.topic-row').first().click();
 await expect(page.locator('[data-focused-topic]')).not.toHaveAttribute('data-focused-topic','');
 await page.getByRole('button',{name:'Clear shop focus'}).click();
 await expect(page.locator('[data-focused-topic]')).toHaveAttribute('data-focused-topic','');
 await page.getByRole('button',{name:'Trends view',exact:true}).click();
 await page.getByRole('textbox',{name:'Find a recorded topic across countries'}).fill('moon');
 await page.locator('.trend-search-results button').first().click();
 await expect(page.locator('.topic-journey h4').first()).toHaveText('Return to the moon');
 await page.locator('.journey-scroll').getByRole('button',{name:'United States'}).click();
 await expect(page.locator('.city-heading h2')).toContainText('United States');
 await expect(page.locator('.topic-journey h4').first()).toHaveText('Return to the moon');
 await page.getByRole('button',{name:'Look through the AI lens'}).click();
 await expect(page.locator('.topic-journey h4').first()).not.toHaveText('Return to the moon');
 expect(errors).toEqual([]);
});

test('French translations preserve originals and the recorded Cornell query is explorable',async({page})=>{
 await page.unroute('**/data/manifest.json');await page.goto('/');
 await page.getByRole('button',{name:'Trends view',exact:true}).click();
 await page.getByRole('button',{name:'Tracked query: cornell 7',exact:true}).click();
 await expect(page.locator('.topic-journey h4').first()).toHaveText('Tracked query: cornell 7');
 await page.locator('.journey-scroll').getByRole('button',{name:'United States'}).click();
 await expect(page.locator('.topic-journey h4').first()).toHaveText('Tracked query: cornell 7');
 await page.locator('#country').selectOption('FR');
 await page.getByRole('button',{name:'List view',exact:true}).click();
 await expect(page.locator('.topic-detail .original-text').first()).toBeVisible();
 const original=await page.locator('.topic-detail .original-text').first().innerText();
 await page.getByRole('button',{name:'English translations',exact:true}).click();
 await expect(page.locator('.topic-detail h3')).toHaveText(original.replace(/^Original: /,''));
});

 test('source coverage exposes successful English sources for an expansion country',async({page})=>{
 await page.unroute('**/data/manifest.json');await page.goto('/');
 await page.locator('#country').selectOption('FR');
 await page.locator('.source-context button').click();
 await expect(page.locator('.section-kicker').filter({hasText:'ENGLISH CONTROL'})).toBeVisible();
 await expect(page.locator('.platform-row').filter({hasText:'YouTube'})).toBeVisible();
 await page.getByText('Source coverage across countries',{exact:true}).click();
 await expect(page.locator('.coverage-countries')).toBeVisible();
 });
