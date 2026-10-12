import { test, expect } from '@playwright/test';
import fs from 'node:fs';

const recording=JSON.parse(fs.readFileSync('public/data/demo-v1/recording.json','utf8'));
const item={id:'social',title:'Claude Code demo on Instagram',url:'https://www.instagram.com/reel/example/',rank:3,source:'google_search',surface:'scan_instagram_test',query:'site:instagram.com "Claude Code"',language:'en',snippet:'Claude Code demo · 2 days ago · 12K likes',observationId:'obs',observedAt:'2026-10-05T12:00:00Z',discovery:{platform:'instagram',engine:'google_search',relevance:1,freshnessLabel:'2 days ago',engagementLabels:['12K likes'],basis:'indexed-search'}};
const scanRecording={...recording,mode:'recording',countries:recording.countries.filter((c:any)=>c.code==='SG'),windows:['2026-10-05T12:00:00Z'],snapshots:[{country:'SG',window:'2026-10-05T12:00:00Z',profile:'english',coverage:[{source:'google_search',surface:'scan_instagram_test',query:item.query,status:'success',itemCount:1,observedCountry:'SG',observedAt:item.observedAt,observationId:'obs',bytes:100,promoted:false}],topics:[{id:'social',label:item.title,aliases:[],category:'ai',score:1/3,count:1,firstSeen:item.observedAt,platforms:{google_search:1/3},items:[item]}],events:[]}]};
const completed={id:'a'.repeat(24),keyword:'Claude Code',countries:['SG'],createdAt:'2026-10-05T12:00:00Z',status:'partial',planned:7,completed:7,events:[{country:'SG',source:'google_search',channel:'instagram',query:item.query,status:'success',itemCount:1,observedAt:item.observedAt,fallback:false}],recording:scanRecording};

test.beforeEach(async({page})=>{
  await page.route('**/data/manifest.json',r=>r.fulfill({contentType:'application/json',body:fs.readFileSync('public/data/demo-manifest.json','utf8')}));
  await page.route('**/data/scans/index.json',r=>r.fulfill({json:[]}));
});

test('a new keyword streams real steps, evidence and a country comparison',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/scans',r=>r.fulfill({status:202,json:{cached:false,scan:{...completed,status:'queued',completed:0,events:[],recording:null}}}));
  await page.route('**/api/scans/*',r=>r.fulfill({json:completed}));
  await page.goto('/');
  await page.getByRole('textbox',{name:'Keyword to scan'}).fill('Claude Code');
  await page.getByRole('button',{name:'Explore the world',exact:true}).click();
  await expect(page.getByText('Deploying geographic observers…')).toBeVisible();
  await expect(page.locator('.scan-outcome')).toHaveText('partial · 7/7 signals');
  await expect(page.locator('.scan-findings a')).toHaveText('Claude Code demo on Instagram');
  await expect(page.getByText('12K likes · snippet')).toBeVisible();
  await page.getByLabel('Scan platform').selectOption('instagram');
  await expect(page.locator('.scan-findings article')).toHaveCount(1);
  await page.getByLabel('Scan platform').selectOption('tiktok');
  await expect(page.locator('.scan-findings article')).toHaveCount(0);
  await page.getByRole('button',{name:'Close scan'}).click();
  await expect(page.locator('.scan-result')).toHaveCount(0);
  await expect(page.getByText('Synthetic demonstration · illustrative topics and arrivals')).toBeVisible();
  expect(errors).toEqual([]);
});

test('cached recommendation opens without making a live request and stays within mobile width',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.route('**/data/scans/index.json',r=>r.fulfill({json:[completed]}));
  await page.route('**/data/scans/*.json',r=>r.fulfill({json:completed}));
  // The index route must take priority over the snapshot wildcard.
  await page.route('**/data/scans/index.json',r=>r.fulfill({json:[completed]}));
  let liveRequests=0;
  await page.route('**/api/scans',r=>{liveRequests++;return r.fulfill({status:503,json:{error:'offline'}});});
  await page.goto('/');
  await page.getByRole('button',{name:'Claude Code Snapshot'}).click();
  await expect(page.locator('.scan-result-heading')).toContainText('SNAPSHOT');
  await expect(page.locator('.scan-findings article')).toHaveCount(1);
  expect(liveRequests).toBe(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
});

test('live service failure is visible and preserves the recording',async({page})=>{
  await page.route('**/api/scans',r=>r.fulfill({status:422,json:{error:'This scan exceeds the remaining traffic budget. Choose fewer countries.'}}));
  await page.goto('/');
  await page.getByRole('textbox',{name:'Keyword to scan'}).fill('BYD');
  await page.getByRole('button',{name:'Explore the world',exact:true}).click();
  await expect(page.getByText('This scan exceeds the remaining traffic budget. Choose fewer countries.')).toBeVisible();
  await expect(page.getByText('Synthetic demonstration · illustrative topics and arrivals')).toBeVisible();
});

test('search works before any scheduled recording exists',async({page})=>{
  await page.route('**/data/manifest.json',r=>r.fulfill({status:404,body:'Not found'}));
  await page.route('**/api/scans',r=>r.fulfill({status:202,json:{cached:false,scan:{...completed,status:'queued',completed:0,events:[],recording:null}}}));
  await page.route('**/api/scans/*',r=>r.fulfill({json:completed}));
  await page.goto('/');
  await page.getByRole('textbox',{name:'Keyword to scan'}).fill('Claude Code');
  await page.getByRole('button',{name:'Explore the world',exact:true}).click();
  await expect(page.locator('.scan-outcome')).toHaveText('partial · 7/7 signals');
  await expect(page.locator('.scan-findings article')).toHaveCount(1);
});

test('two viewpoints can be compared and filtered independently',async({page})=>{
  const usItem={...item,id:'us-social',title:'Claude Code discussion in the US',observationId:'us-obs'};
  const usSnapshot={...scanRecording.snapshots[0],country:'US',topics:[{...scanRecording.snapshots[0].topics[0],id:'us-social',label:usItem.title,items:[usItem]}]};
  const both={...completed,countries:['SG','US'],planned:14,completed:14,recording:{...scanRecording,countries:recording.countries.filter((c:any)=>['SG','US'].includes(c.code)),snapshots:[...scanRecording.snapshots,usSnapshot]}};
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.route('**/api/scans',r=>r.fulfill({json:{cached:true,scan:both}}));
  await page.goto('/');
  await page.getByRole('button',{name:'List view',exact:true}).click();
  await page.getByRole('textbox',{name:'Keyword to scan'}).fill('Claude Code');
  await page.getByRole('button',{name:'Explore the world',exact:true}).click();
  await expect(page.locator('.scan-world button')).toHaveCount(2);
  await expect(page.locator('.signal-country-groups .signal-dot')).toHaveCount(2);
  await page.locator('.signal-country-groups .signal-dot').first().click();
  await expect(page.locator('.signal-inspector')).toContainText('Not in sample');
  await expect(page.locator('.scan-findings article')).toHaveCount(2);
  await page.locator('.scan-world button').filter({hasText:'United States'}).click();
  await expect(page.locator('.scan-findings article')).toHaveCount(1);
  await expect(page.locator('.scan-findings a')).toHaveText(usItem.title);
  await page.getByRole('button',{name:'Compare viewpoints',exact:true}).click();
  await expect(page.getByText('topic overlap',{exact:true})).toBeVisible();
  await expect(page.locator('.overlap strong')).toHaveText('0%');
});


test('concept selection previews terms before collection and keeps identity on refresh',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  const concept=JSON.parse(fs.readFileSync('config/market-concepts.json','utf8')).concepts.find((c:any)=>c.id==='bubble-tea');
  const conceptItem={...item,title:'Bubble tea shop',query:'"bubble tea"',surface:'scan_web_test',discovery:{...item.discovery,platform:'web'}};
  const snapshot={...scanRecording.snapshots[0],coverage:[{...scanRecording.snapshots[0].coverage[0],surface:conceptItem.surface,query:conceptItem.query}],topics:[{...scanRecording.snapshots[0].topics[0],items:[conceptItem]}]};
  const result={...completed,concept,keyword:concept.label,recording:{...scanRecording,snapshots:[snapshot]}};
  const requests:any[]=[];
  await page.route('**/api/scans',r=>{requests.push(r.request().postDataJSON());return r.fulfill({json:{cached:true,scan:result}});});
  await page.goto('/');
  await page.getByRole('button',{name:/Food & drinks Bubble tea & boba/}).click();
  await expect(page.locator('.concept-selection')).toContainText('珍珠奶茶');
  expect(requests).toHaveLength(0);
  await page.getByRole('button',{name:'Explore concept',exact:true}).click();
  expect(requests[0]).toMatchObject({conceptId:'bubble-tea',countries:['US','SG','JP','KR']});
  await expect(page.getByRole('region',{name:'Term patterns across markets'})).toBeVisible();
  await page.getByRole('button',{name:'bubble tea in SG: 1 links'}).click();
  await expect(page.locator('.scan-findings article')).toHaveCount(1);
  await page.getByRole('button',{name:'Refresh scan live'}).click();
  expect(requests[1]).toMatchObject({conceptId:'bubble-tea',refresh:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
});


test('saved scan links restore concept and viewpoints',async({page})=>{
  const concept=JSON.parse(fs.readFileSync('config/market-concepts.json','utf8')).concepts[0];
  await page.route(`**/data/scans/${completed.id}.json`,r=>r.fulfill({json:{...completed,keyword:concept.label,concept}}));
  await page.goto(`/?scan=${completed.id}`);
  await expect(page.locator('.scan-result-heading h3')).toHaveText('Short dramas');
  await expect(page.locator('.concept-selection')).toContainText('microdrama');
  await expect(page.locator('.scan-world button')).toHaveCount(1);
});
