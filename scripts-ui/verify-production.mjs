import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const server=spawn('python3',['-m','http.server','3101','--directory','out','--bind','127.0.0.1'],{stdio:'ignore'});
let browser;
try {
  for(let i=0;i<30;i++){try{if((await fetch('http://127.0.0.1:3101')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch();
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const manifest=JSON.parse(fs.readFileSync('out/data/manifest.json'));
  const recording=JSON.parse(fs.readFileSync('out'+manifest.recordingUrl));
  await page.goto('http://127.0.0.1:3101');
  await page.locator('[data-resident-count]').waitFor({timeout:30000});
  await page.getByRole('button',{name:'English control',exact:true}).click();
  const snapshot=recording.snapshots.find(s=>s.country==='SG'&&s.profile==='english');
  const expected=[...snapshot.topics].sort((a,b)=>b.count-a.count||a.id.localeCompare(b.id)).slice(0,48).reduce((n,t)=>n+t.items.length,0);
  await page.locator(`[data-resident-count="${expected}"]`).waitFor({timeout:30000});
  await page.locator('#country').selectOption('JP');
  await page.getByRole('button',{name:'List view',exact:true}).click();
  await page.locator('.topic-card').first().waitFor();
  await page.getByRole('button',{name:'About this recording'}).click();
  await page.getByRole('button',{name:'Open synthetic demonstration'}).click();
  await page.getByText('Synthetic demonstration · illustrative topics and arrivals').waitFor();
  await page.getByRole('button',{name:'City view',exact:true}).click();
  await page.locator('[data-resident-count]').waitFor();
  await page.getByRole('button',{name:'Next snapshot'}).click();
  await page.waitForTimeout(300);
  assert.deepEqual(errors,[]);
  console.log('Production static server: real visitors, profile/country switches, list fallback and synthetic replay passed without collector access.');
} finally { await browser?.close();server.kill(); }
