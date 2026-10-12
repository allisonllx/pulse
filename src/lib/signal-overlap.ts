import { coverageKey, Item, Snapshot, success } from './recording';
import { Scan, scanItems } from './scans';

export type VisualSignal = { id:string; label:string; url?:string; present:string[]; unknown:string[]; ranks:Record<string,number> };

/** Match exact result identity. Missing collection is never an exclusive result. */
export function scanSignals(scan:Scan,channel='all'):VisualSignal[] {
  const snapshots=scan.recording?.snapshots??[];
  const coverage=new Map(scan.countries.map(c=>[c,new Set(snapshots.filter(s=>s.country===c).flatMap(s=>s.coverage.filter(v=>success(v.status)).map(coverageKey)))]));
  const grouped=new Map<string,{item:Item;present:Set<string>;keys:Set<string>;ranks:Record<string,number>}>();
  for(const item of scanItems(scan)) {
    if(channel!=='all'&&item.discovery?.platform!==channel)continue;
    const group=grouped.get(item.id)??{item,present:new Set<string>(),keys:new Set<string>(),ranks:{}};
    group.present.add(item.country);group.keys.add(coverageKey(item));
    group.ranks[item.country]=Math.min(group.ranks[item.country]??Infinity,item.rank);
    grouped.set(item.id,group);
  }
  return [...grouped.entries()].map(([id,g])=>({id,label:g.item.title,url:g.item.url,present:scan.countries.filter(c=>g.present.has(c)),unknown:scan.countries.filter(c=>!g.present.has(c)&&![...g.keys].some(k=>coverage.get(c)?.has(k))),ranks:g.ranks}));
}

/** Topic identity comes from the recording's existing cluster engine. */
export function topicSignals(left:Snapshot|undefined,right:Snapshot|undefined,ai=false,source='all'):VisualSignal[] {
  if(!left||!right||left.country===right.country||left.profile!==right.profile||left.window!==right.window)return [];
  const snapshots=[left,right];
  const coverage=snapshots.map(s=>new Set(s.coverage.filter(c=>success(c.status)&&(source==='all'||c.source===source)).map(coverageKey)));
  const signals=new Map<string,VisualSignal>();
  snapshots.forEach((s,index)=>s.topics.filter(t=>!ai||t.category==='ai').forEach(t=>{
    const items=t.items.filter(i=>(source==='all'||i.source===source)&&coverage[index].has(coverageKey(i)));
    if(!items.length)return;
    const signal=signals.get(t.id)??{id:t.id,label:t.label,url:items[0].url,present:[],unknown:[],ranks:{}};
    signal.present.push(s.country);signal.ranks[s.country]=Math.min(...items.map(i=>i.rank));
    signals.set(t.id,signal);
  }));
  for(const signal of signals.values()) {
    const keys=new Set(snapshots.flatMap(s=>s.topics.filter(t=>t.id===signal.id).flatMap(t=>t.items.filter(i=>source==='all'||i.source===source).map(coverageKey))));
    signal.unknown=snapshots.filter((s,index)=>!signal.present.includes(s.country)&&![...keys].some(k=>coverage[index].has(k))).map(s=>s.country);
  }
  return [...signals.values()];
}
