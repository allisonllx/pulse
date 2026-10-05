import { coverageKey, Profile, Recording, Snapshot, Source, success, Topic } from './recording';

const keysFor = (s:Snapshot|undefined,source:Source|'all') => new Set(s?.coverage.filter(c=>success(c.status)&&(source==='all'||source===c.source)).map(coverageKey)??[]);
const appearances = (s:Snapshot,keys:Set<string>,id?:string) => s.topics.filter(t=>!id||id.startsWith('watch:')||t.id===id).flatMap(t=>t.items.filter(i=>keys.has(coverageKey(i))&&(!id?.startsWith('watch:')||i.surface==='watch_rss'&&i.query===id.slice(6)&&(id.slice(6)!=='cornell 7'||/cornell|コーネル|कॉर्नेल|코넬|康奈[尔爾]/iu.test(i.title)))));
export function rankedTrends(current:Snapshot|undefined,previous:Snapshot|undefined,source:Source|'all'='all',ai=false) {
  if(!current)return [];
  const currentKeys=keysFor(current,source),priorKeys=keysFor(previous,source);
  const common=new Set([...currentKeys].filter(k=>priorKeys.has(k)));
  const contiguous=!!previous&&previous.country===current.country&&previous.profile===current.profile&&Date.parse(current.window)-Date.parse(previous.window)===21600000;
  const scope=contiguous&&common.size?common:currentKeys;
  const total=appearances(current,scope).reduce((n,i)=>n+1/i.rank,0);
  const previousTotal=previous?appearances(previous,scope).reduce((n,i)=>n+1/i.rank,0):0;
  return current.topics.filter(t=>!ai||t.category==='ai').map(topic=>{
    const items=topic.items.filter(i=>scope.has(coverageKey(i)));
    const share=total?items.reduce((n,i)=>n+1/i.rank,0)/total:0;
    const before=previous&&contiguous&&common.size?appearances(previous,scope,topic.id):null;
    const previousShare=before&&previousTotal?before.reduce((n,i)=>n+1/i.rank,0)/previousTotal:0;
    return {topic,count:items.length,share,delta:before?items.length-before.length:null,change:before?share-previousShare:null,comparableSurfaces:before?common.size:0};
  }).filter(t=>t.count>0).sort((a,b)=>b.share-a.share||a.topic.id.localeCompare(b.topic.id));
}

export function topicJourney(data:Recording,id:string,profile:Profile,source:Source|'all',anchor:Snapshot|undefined,through:string) {
  // Hold surface/query composition fixed for the entire matrix. A failed or absent
  // required surface is a gap, while a successful sample without this topic is 0.
  const reference=id.startsWith('watch:')?new Set(data.snapshots.filter(s=>s.profile===profile&&Date.parse(s.window)<=Date.parse(through)).flatMap(s=>s.coverage.filter(c=>c.surface==='watch_rss'&&c.query===id.slice(6)&&(source==='all'||c.source===source)).map(coverageKey))):keysFor(anchor,source);
  const windows=data.windows.filter(w=>Date.parse(w)<=Date.parse(through));
  const rows=data.countries.map(country=>{
    const cells=windows.map(window=>{
      const snapshot=data.snapshots.find(s=>s.country===country.code&&s.profile===profile&&s.window===window);
      const available=keysFor(snapshot,source);
      const complete=!!snapshot&&reference.size>0&&[...reference].every(k=>available.has(k));
      const evidence=snapshot?appearances(snapshot,reference,id):[];
      const observed=evidence.length>0;
      const total=snapshot?appearances(snapshot,reference).reduce((n,i)=>n+1/i.rank,0):0;
      return {window,count:complete?evidence.length:null,share:complete&&total?evidence.reduce((n,i)=>n+1/i.rank,0)/total:null,observed,partial:observed&&!complete,firstAt:evidence.length?evidence.map(i=>i.observedAt).sort()[0]:null};
    });
    const first=cells.find(c=>c.observed);
    return {country,cells,firstWindow:first?.window??null,firstAt:first?.firstAt??null};
  });
  const detections=rows.filter(r=>r.firstAt).sort((a,b)=>a.firstAt!.localeCompare(b.firstAt!)||a.country.code.localeCompare(b.country.code));
  return {windows,rows,detections,referenceSurfaces:reference.size};
}

export function knownTopics(data:Recording,profile:Profile,source:Source|'all',through:string) {
  const topics=new Map<string,Topic>();
  data.snapshots.filter(s=>s.profile===profile&&Date.parse(s.window)<=Date.parse(through)).forEach(s=>s.topics.filter(t=>t.items.some(i=>source==='all'||i.source===source)).forEach(t=>topics.set(t.id,t)));
  const watched=new Set(data.snapshots.filter(s=>s.profile===profile&&Date.parse(s.window)<=Date.parse(through)).flatMap(s=>s.coverage.filter(c=>c.surface==='watch_rss'&&c.query&&(source==='all'||c.source===source)).map(c=>c.query!)));
  for(const query of watched)topics.set('watch:'+query,{id:'watch:'+query,label:'Tracked query: '+query,aliases:[query],category:'watch-query',score:0,count:0,firstSeen:through,platforms:{},items:[]});
  return [...topics.values()];
}
