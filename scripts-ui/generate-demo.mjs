import { mkdirSync, writeFileSync } from 'node:fs';
const countries = [
  ['SG','Singapore','🇸🇬','en'], ['US','United States','🇺🇸','en'], ['GB','United Kingdom','🇬🇧','en'],
  ['JP','Japan','🇯🇵','ja'], ['IN','India','🇮🇳','hi'], ['BR','Brazil','🇧🇷','pt']
].map(([code,name,flag,language]) => ({code,name,flag,language}));
const seeds = [
  ['ai-agents','AI agents','ai', ['AIエージェント','Agentes de IA']],
  ['moon','Return to the moon','news', []],
  ['indie','Indie game worlds','gaming', []],
  ['coding','Coding companions','ai', []],
  ['music','New music Friday','music', []],
  ['film','The next big film','culture', []],
  ['robotics','Everyday robotics','technology', []],
  ['cities','Greener cities','news', []],
  ['models','Open model releases','ai', []],
  ['food','A taste of home','culture', []],
  ['sport','Match day','culture', []],
  ['space','The night sky','news', []],
  ['local-sg','Hawker stories','culture', []],
  ['local-jp','Tokyo game scene','gaming', []],
  ['local-br','Brazilian soundwaves','music', []],
  ['local-in','Monsoon stories','news', []]
];
const sources = ['google_news','google_search','youtube'];
const queries = ['AI agents','AI coding tools','latest AI models','music','gaming'];
const windows = Array.from({length: 8}, (_,i) => new Date(Date.UTC(2026,9,5,0) + i*6*3600000).toISOString());
const snapshots = [];
const previous = new Map();
for (let wi=0;wi<windows.length;wi++) for (let ci=0;ci<countries.length;ci++) for (const profile of ['local','english']) {
  const country = countries[ci], window = windows[wi];
  const coverage = [];
  const topics = new Map();
  for (const [si,source] of sources.entries()) {
    const surface = source === 'google_news' ? 'headlines' : 'search';
    const qs = profile === 'english' && source !== 'google_news' ? queries : [null];
    for (const query of qs) {
      const oid = `demo-${country.code}-${wi}-${profile}-${source}-${query ?? 'headlines'}`;
      const failed = country.code === 'JP' && wi === 3 && source === 'youtube';
      coverage.push({source,surface,query,status:failed?'blocked':'success',itemCount:failed?0:20,observedCountry:country.code,observedAt:window,observationId:oid,bytes:0,promoted:wi>0});
      if (failed) continue;
      const selected = seeds.filter((s,index) => !s[0].startsWith('local-') || s[0] === `local-${country.code.toLowerCase()}`).filter((s,index) => query ? (query.toLowerCase().includes('ai') ? s[2]==='ai' : query === 'music' ? s[2]==='music' : s[2]==='gaming') : true);
      for (let rank=1;rank<=20;rank++) {
        const seed = selected[(rank+ci+si+Math.floor(wi/2))%selected.length];
        const [id,label,category,aliases]=seed;
        const item = {id:`${source}-${id}-${rank % 4}`,title:`${label} · illustrative result ${rank % 4 + 1}`,url:`https://example.com/worldview-demo/${id}/${source}/${rank}`,rank,source,surface,query,language:profile==='english'?'en':country.language,snippet:'Synthetic example for exploring the city. This is not a harvested result.',observationId:oid,observedAt:window};
        // Each result has a distinct platform ID; repeats across surfaces remain appearances.
        item.id=`${source}-${id}-${rank}-${query ?? 'discovery'}`;
        if (!topics.has(id)) topics.set(id,{id,label,aliases,category,score:0,count:0,firstSeen:windows[0],platforms:{},items:[]});
        const topic = topics.get(id); topic.items.push(item); topic.count++; topic.score+=1/rank; topic.platforms[source]=(topic.platforms[source]??0)+1;
      }
    }
  }
  const events=[];
  for (const c of coverage) {
    if (c.status!=='success') continue;
    const key=`${country.code}|${profile}|${c.source}|${c.surface}|${c.query??''}`;
    const current = new Map([...topics.values()].flatMap(t=>t.items.filter(i=>i.observationId===c.observationId).map(i=>[i.id,t.id])));
    const prev=previous.get(key) ?? new Map();
    for (const [id,tid] of current) if (!prev.has(id)) events.push({id:`${c.observationId}-arrival-${id}`,topicId:tid,itemId:id,source:c.source,kind:'arrival',window});
    for (const [id,tid] of prev) if (!current.has(id)) events.push({id:`${c.observationId}-departure-${id}`,topicId:tid,itemId:id,source:c.source,kind:'departure',window});
    previous.set(key,current);
  }
  snapshots.push({country:country.code,window,profile,coverage,topics:[...topics.values()].sort((a,b)=>b.score-a.score),events});
}
const recording={schemaVersion:1,mode:'demo',generatedAt:windows.at(-1),clusterVersion:'demo-illustrative-v1',countries,windows,snapshots};
mkdirSync('public/data/demo-v1',{recursive:true});
writeFileSync('public/data/demo-v1/recording.json',JSON.stringify(recording));
const coverage=snapshots.flatMap(s=>s.coverage);
const manifest={schemaVersion:1,datasetVersion:'demo-v1',generatedAt:recording.generatedAt,mode:'demo',recordingUrl:'/data/demo-v1/recording.json',countries:countries.map(c=>c.code),windows,clusterVersion:recording.clusterVersion,coverage:{successful:coverage.filter(c=>c.status==='success').length,failed:coverage.filter(c=>c.status!=='success').length}};
writeFileSync('public/data/manifest.json',JSON.stringify(manifest,null,2));
writeFileSync('public/data/demo-manifest.json',JSON.stringify(manifest,null,2));
console.log(`Generated synthetic demonstration: ${snapshots.length} snapshots. No real observations.`);
