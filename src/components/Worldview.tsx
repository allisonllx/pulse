'use client';
import dynamic from 'next/dynamic';
import { Component, ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, ArrowRight, Box, Check, ChevronDown, ChevronLeft, ChevronRight, Clock3, Database, Globe2, Layers3, List, LoaderCircle, Maximize2, Pause, Play, Search, Sparkles, X } from 'lucide-react';
import Atlas from './Atlas';
import { compareSnapshots, Country, dateLabel, filterTopics, Manifest, PLATFORMS, Profile, readRecording, Recording, safeUrl, snapshotAt, Source, success, Topic } from '@/lib/recording';
import { visibleEvents } from '@/lib/visitors';
const City = dynamic(() => import('./City'), { ssr: false, loading: () => <div className="city-loading"><LoaderCircle className="spin" /><span>Opening the city…</span></div> });
class CityBoundary extends Component<{ children: ReactNode; onFailure: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onFailure(); }
  render() { return this.state.failed ? null : this.props.children; }
}
export default function Worldview() {
  const [recording, setRecording] = useState<Recording | null>(null);
  const [country, setCountry] = useState('SG'), [profile, setProfile] = useState<Profile>('local');
  const [windowIndex, setWindowIndex] = useState(0), [selected, setSelected] = useState<string | null>(null);
  const [platform, setPlatform] = useState<Source | 'all'>('all'), [ai, setAi] = useState(false), [query, setQuery] = useState('');
  const [playing, setPlaying] = useState(false), [reduced, setReduced] = useState(false), [view, setView] = useState<'city'|'list'>('city');
  const [compare, setCompare] = useState(false), [other, setOther] = useState('US'), [method, setMethod] = useState(false);
  const [error, setError] = useState(''), [demoOverride, setDemoOverride] = useState(false), [updated, setUpdated] = useState(0);
  const version = useRef('');
  const recordingRef = useRef<Recording | null>(null);
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)'); const update = () => setReduced(media.matches); update(); media.addEventListener('change', update);
    const probe = document.createElement('canvas'); if (matchMedia('(max-width: 620px)').matches || (!probe.getContext('webgl2') && !probe.getContext('webgl'))) setView('list');
    return () => media.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(demoOverride ? '/data/demo-manifest.json' : '/data/manifest.json', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error('No published recording yet. Publish a snapshot from the local collector.');
        const manifest = await response.json() as Manifest;
        if (manifest.schemaVersion !== 1 || typeof manifest.recordingUrl !== 'string' || !/^\/data\/[a-zA-Z0-9_./-]+\.json$/.test(manifest.recordingUrl) || manifest.recordingUrl.includes('..')) throw new Error('Invalid published manifest.');
        const key = `${demoOverride}:${manifest.datasetVersion}`;
        if (version.current === key) return;
        const dataResponse = await fetch(manifest.recordingUrl, { cache: 'no-store', signal: controller.signal });
        if (!dataResponse.ok) throw new Error('The recording is temporarily unavailable. The previous view is preserved.');
        const data = readRecording(await dataResponse.json());
        if (active) {
          const prior = recordingRef.current; recordingRef.current=data;
          version.current = key; setRecording(data); setError(''); setUpdated(n=>n+1);
          setCountry(c => data.countries.some(x=>x.code===c)?c:data.countries[0]?.code??'SG');
          setWindowIndex(i => {
            if ((!prior && data.mode==='recording') || (prior && prior.mode===data.mode && i===prior.windows.length-1)) return Math.max(0,data.windows.length-1);
            const oldFrame=prior?.windows[i];const next=oldFrame?data.windows.indexOf(oldFrame):-1;
            return next>=0?next:Math.min(i,Math.max(0,data.windows.length-1));
          });
        }
      } catch (e) { if (active && !(e instanceof Error && e.name==='AbortError')) setError(e instanceof Error ? e.message : 'Could not load recording.'); }
    }
    void load(); const interval = setInterval(()=>void load(),60000);
    return () => { active = false; controller.abort(); clearInterval(interval); };
  }, [demoOverride]);
  useEffect(() => {
    if (!playing || !recording || recording.windows.length<2) return;
    const timer = setInterval(()=>setWindowIndex(i => { if (i >= recording.windows.length - 1) { setPlaying(false); return i; } return i+1; }), 10000);
    return () => clearInterval(timer);
  }, [playing,recording]);
  useEffect(() => { if (method) { const handler=(e:KeyboardEvent)=>{if(e.key==='Escape')setMethod(false);}; globalThis.addEventListener('keydown',handler); return()=>globalThis.removeEventListener('keydown',handler); } },[method]);
  const window = recording?.windows[windowIndex];
  const snapshot = useMemo(()=>recording && window ? snapshotAt(recording,country,window,profile):undefined,[recording,country,window,profile]);
  const topics = useMemo(()=>filterTopics(snapshot,ai,platform,query),[snapshot,ai,platform,query]);
  const universe = useMemo(()=> {
    const all = new Map<string,Topic>(); recording?.snapshots.filter(s=>s.country===country&&s.profile===profile).forEach(s=>s.topics.forEach(t=>{if(!all.has(t.id))all.set(t.id,t);}));
    return [...all.values()];
  },[recording,country,profile]);
  const cityTopics=useMemo(()=>universe.length<=48?universe:[...universe].sort((a,b)=>b.count-a.count||a.id.localeCompare(b.id)).slice(0,48),[universe]);
  const cityIds=new Set(cityTopics.map(t=>t.id));
  const cityVisible=topics.filter(t=>cityIds.has(t.id));
  const activeTopic = topics.find(t=>t.id===selected) ?? topics[0];
  const activeCountry = recording?.countries.find(c=>c.code===country);
  const successful = snapshot?.coverage.filter(c=>success(c.status))??[];
  const appearances = topics.reduce((sum,t)=>sum+t.count,0);
  const events = visibleEvents(cityTopics,snapshot?.events??[],ai,platform,query);
  const comparison = recording && window ? compareSnapshots(snapshot,snapshotAt(recording,other,window,profile),ai,platform) : null;
  function chooseCountry(code:string) { setCountry(code); setSelected(null); if(code===other) setOther(recording?.countries.find(c=>c.code!==code)?.code??'US'); }
  function togglePlay() { if (!playing && windowIndex >= (recording?.windows.length??1)-1) setWindowIndex(0); setPlaying(v=>!v); }
  if (!recording) return <main className="boot"><Globe2 size={42}/><h1>Worldview</h1><p>{error||'Opening a little world of internet attention…'}</p>{error&&<button onClick={()=>setDemoOverride(true)}>Explore demonstration</button>}</main>;
  return <main className="worldview">
    <header className="topbar">
      <a className="brand" href="/" aria-label="Worldview home"><span className="brand-mark"><Globe2 size={23}/></span>worldview<span className="brand-dot">.</span></a>
      <span className="brand-note">A LITTLE WORLD OF INTERNET ATTENTION</span>
      <div className="top-actions"><span className="recording-status"><i/>{recording.mode==='demo'?'DEMONSTRATION':'RECORDED OBSERVATIONS'}</span><button className="icon-button" onClick={()=>setMethod(true)} aria-label="About this recording"><Database size={17}/></button></div>
    </header>
    <div className="workspace">
      <aside className="left-panel">
        <div className="section-kicker"><Globe2 size={13}/> YOUR VIEWPOINT</div>
        <h1>The internet,<br/>from here.</h1>
        <p className="intro">Same world. Different windows.<br/>Step into a country’s information city.</p>
        <Atlas countries={recording.countries} selected={country} onSelect={chooseCountry}/>
        <label className="select-label" htmlFor="country">VIEWING FROM</label>
        <div className="country-select"><span>{activeCountry?.flag}</span><select id="country" value={country} onChange={e=>chooseCountry(e.target.value)}>{recording.countries.map(c=><option value={c.code} key={c.code}>{c.name}</option>)}</select><ChevronDown size={15}/></div>
        <div className="profile-control" role="group" aria-label="Observation profile"><button className={profile==='local'?'active':''} onClick={()=>{setProfile('local');setSelected(null);}}>Local view</button><button className={profile==='english'?'active':''} onClick={()=>{setProfile('english');setSelected(null);}}>English control</button></div>
        <p className="profile-note">{profile==='local'?'Local-language discovery with regional settings.':'Same English queries and fixed platform settings.'}</p>
        <div className="divider"/>
        <div className="section-kicker"><Layers3 size={13}/> PLATFORM STREETS</div>
        <button className={`platform-row ${platform==='all'?'selected':''}`} onClick={()=>setPlatform('all')}><span className="platform-symbol all"><Layers3 size={13}/></span><span>All platforms</span><span className="count">{snapshot?.topics.reduce((n,t)=>n+t.count,0)??0}</span>{platform==='all'&&<Check size={13}/>}</button>
        {PLATFORMS.map(p=>{
          const coverage=snapshot?.coverage.filter(c=>c.source===p.id)??[];
          const count=coverage.filter(c=>success(c.status)).reduce((n,c)=>n+c.itemCount,0);
          return <button key={p.id} className={`platform-row ${platform===p.id?'selected':''}`} onClick={()=>setPlatform(p.id)}><span className="platform-symbol" style={{color:p.color,background:`${p.color}18`}}>{p.short[0]}</span><span>{p.label}</span><span className="count">{coverage.length ? count : '—'}</span>{platform===p.id&&<Check size={13}/>}</button>;
        })}
        <button className={`ai-switch ${ai?'active':''}`} onClick={()=>setAi(!ai)} aria-pressed={ai}><Sparkles size={16}/><span>Look through the AI lens</span><span className="switch"><i/></span></button>
        <div className="left-footer"><span className="tiny-dot"/> {recording.countries.length} viewpoints · {recording.windows.length} frames<button onClick={()=>setMethod(true)}>How to read this <ArrowUpRight size={12}/></button></div>
      </aside>
      <section className="city-panel" aria-label="Country city">
        <div className="city-heading"><div><div className="section-kicker">{activeCountry?.flag} {country} / {profile==='local'?'LOCAL PERSPECTIVE':'ENGLISH CONTROL'}</div><h2>{activeCountry?.name}<span>Information city</span></h2></div><div className="view-switch" role="group" aria-label="View mode"><button aria-label="City view" aria-pressed={view==='city'} className={view==='city'?'active':''} onClick={()=>setView('city')}><Box size={17}/></button><button aria-label="List view" aria-pressed={view==='list'} className={view==='list'?'active':''} onClick={()=>setView('list')}><List size={17}/></button></div></div>
        <div className="demo-banner">{recording.mode==='demo'?<><span className="tiny-dot"/> Synthetic demonstration · illustrative topics and arrivals</>:<><span className="tiny-dot"/> Recorded {window?dateLabel(window,true):'—'} SGT · public-page samples</>}</div>
        {error&&<div className="fetch-error" role="status">{error}</div>}
        <div className="city-stage">
          <div className="city-halo"/>{view==='city'&&universe.length>48&&<div className="city-cap-note">{cityVisible.length} of {topics.length} topics in the city · use List view for all topics</div>}
          {topics.length===0&&(view!=='city'||!events.some(e=>e.kind==='departure'))?<div className="empty-state"><Layers3 size={32}/><h3>No observations in this view</h3><p>{snapshot?'Try another platform, lens, or search.':'No sample was collected for this country and time.'}</p><button onClick={()=>{setPlatform('all');setAi(false);setQuery('');}}>Clear filters</button></div>:view==='city'?<CityBoundary onFailure={()=>setView('list')}><City allTopics={cityTopics} visible={cityVisible} selected={activeTopic?.id??null} events={events} onSelect={setSelected} reduced={reduced} animate={!reduced} frameKey={`${country}-${profile}-${window}-${updated}`}/></CityBoundary>:<div className="list-view">{topics.map(t=><button className={`topic-card ${activeTopic?.id===t.id?'selected':''}`} key={t.id} onClick={()=>setSelected(t.id)}><span className="topic-category">{t.category}</span><h3>{t.label}</h3><span>{t.count} sampled appearances</span><div className="mini-bars">{PLATFORMS.map(p=><i key={p.id} style={{background:p.color,flex:t.items.filter(i=>i.source===p.id).length||.01}}/>)}</div></button>)}</div>}
        </div>
        <div className="city-bottom"><div className="city-instructions"><Maximize2 size={13}/>{view==='city'?'Drag to orbit · scroll to zoom · click a shop':'Select a topic to inspect its evidence'}</div><div className="city-legend"><span><i className="legend-shop"/>Topic = shop</span><span><i className="legend-person"/>Result = visitor</span></div></div>
        <div className="stats-strip"><div><span>TOPICS IN VIEW</span><strong>{topics.length.toString().padStart(2,'0')}</strong></div><div><span>SAMPLED APPEARANCES</span><strong>{appearances}<small>results</small></strong></div><div><span>COLLECTION COVERAGE</span><strong>{successful.length}<small>/ {snapshot?.coverage.length??0} surfaces</small></strong></div><button className={compare?'active':''} onClick={()=>setCompare(!compare)}><Globe2 size={16}/><span>Compare viewpoints</span><ArrowRight size={15}/></button></div>
      </section>
      <aside className="right-panel">
        {compare?<><div className="section-kicker"><Globe2 size={13}/> ACROSS THE WORLD<button className="close-small" onClick={()=>setCompare(false)} aria-label="Close comparison"><X size={14}/></button></div><h2>A different<br/>window.</h2><label className="select-label" htmlFor="compare-country">COMPARE WITH</label><select id="compare-country" className="compare-select" value={other} onChange={e=>setOther(e.target.value)}>{recording.countries.filter(c=>c.code!==country).map(c=><option key={c.code} value={c.code}>{c.flag} {c.name}</option>)}</select><div className="overlap"><strong>{comparison?.overlap==null?'—':`${Math.round(comparison.overlap*100)}%`}</strong><span>topic overlap</span></div><p className="profile-note">{comparison?`${comparison.commonSurfaces} matching successful surfaces. ${comparison.leftCoverage} vs ${comparison.rightCoverage} available.`:'No comparable successful samples for these settings.'}</p>{comparison&&<><div className="divider"/><div className="section-kicker">SHARED TOPICS · {comparison.shared.length}</div>{comparison.shared.slice(0,8).map(id=><button className="shared-topic" key={id} onClick={()=>{setSelected(id);setCompare(false);}}>{snapshot?.topics.find(t=>t.id===id)?.label}<ArrowUpRight size={13}/></button>)}<div className="comparison-counts"><span>{comparison.leftOnly.length} only here</span><span>{comparison.rightOnly.length} only there</span></div></>}<p className="evidence-note">Overlap describes these samples. It does not measure how an entire country thinks.</p></>:<>
          <div className="section-kicker"><Sparkles size={13}/> IN THIS CITY</div><h2>What’s in<br/>the window?</h2>
          <div className="topic-search"><Search size={14}/><input aria-label="Search topics" placeholder="Find a topic…" value={query} onChange={e=>setQuery(e.target.value)}/>{query&&<button aria-label="Clear topic search" onClick={()=>setQuery('')}><X size={13}/></button>}</div>
          <div className="topic-list">{topics.slice(0,24).map((t,i)=><button key={t.id} className={`topic-row ${activeTopic?.id===t.id?'active':''}`} onClick={()=>{setSelected(t.id);if(!cityIds.has(t.id))setView('list');}}><span className="topic-rank">{String(i+1).padStart(2,'0')}</span><span className="topic-name">{t.label}<small>{t.category==='ai'?'AI & TECHNOLOGY':t.category.toUpperCase()}</small></span><span className="topic-total">{t.count}</span></button>)}</div>
          {activeTopic&&<div className="topic-detail"><div className="detail-title"><span className="section-kicker">INSIDE THE SHOP</span><ArrowUpRight size={14}/></div><h3>{activeTopic.label}</h3><div className="platform-breakdown">{PLATFORMS.filter(p=>activeTopic.items.some(i=>i.source===p.id)).map(p=><span key={p.id}><i style={{background:p.color}}/>{p.short} <b>{activeTopic.items.filter(i=>i.source===p.id).length}</b></span>)}</div><div className="evidence-list">{activeTopic.items.slice(0,3).map((item,i)=>{const url=safeUrl(item.url);return <div key={`${item.observationId}-${item.id}-${i}`} className="evidence-item">{url?<a href={url} target="_blank" rel="noopener noreferrer">{item.title}<ArrowUpRight size={12}/></a>:<span>{item.title}</span>}<small>#{item.rank} · {PLATFORMS.find(p=>p.id===item.source)?.label} · {item.observedAt?dateLabel(item.observedAt):'—'}</small></div>;})}</div><details className="all-evidence"><summary>All {activeTopic.items.length} appearances</summary>{activeTopic.items.map((item,i)=><div className="evidence-item" key={`${item.observationId}-${item.id}-${i}`}>{safeUrl(item.url)?<a href={safeUrl(item.url)!} target="_blank" rel="noopener noreferrer">{item.title}<ArrowUpRight size={12}/></a>:<span>{item.title}</span>}<small>#{item.rank} · {item.source} · {item.observationId}</small></div>)}</details><p className="first-seen"><Clock3 size={12}/>First in recording: {dateLabel(activeTopic.firstSeen)}</p></div>}
        </>}
      </aside>
    </div>
    <footer className="timeline">
      <button className="play-button" onClick={togglePlay} aria-label={playing?'Pause replay':'Play replay'} disabled={recording.windows.length<2}>{playing?<Pause size={18}/>:<Play size={18}/>}</button>
      <div className="timeline-caption"><span>{playing?'PLAYING RECORDING':'RECORDING TIMELINE'}</span><strong>{window?dateLabel(window):'No frames'} <small>SGT</small></strong></div>
      <button className="step-button" aria-label="Previous snapshot" disabled={windowIndex===0} onClick={()=>{setPlaying(false);setWindowIndex(i=>Math.max(0,i-1));}}><ChevronLeft size={17}/></button>
      <div className="timeline-track"><input type="range" aria-label="Recording time" min={0} max={Math.max(0,recording.windows.length-1)} value={windowIndex} onChange={e=>{setPlaying(false);setWindowIndex(Number(e.target.value));}}/><div className="timeline-labels"><span>{recording.windows[0]?dateLabel(recording.windows[0]):'—'}</span><span>{recording.windows.at(-1)?dateLabel(recording.windows.at(-1)!):'—'}</span></div></div>
      <button className="step-button" aria-label="Next snapshot" disabled={windowIndex>=recording.windows.length-1} onClick={()=>{setPlaying(false);setWindowIndex(i=>Math.min(recording.windows.length-1,i+1));}}><ChevronRight size={17}/></button>
      <div className="frame-count">{String(windowIndex+1).padStart(2,'0')}<span>/ {String(recording.windows.length).padStart(2,'0')}</span></div>
    </footer>
    {method&&<MethodDialog recording={recording} demoOverride={demoOverride} onDemo={()=>{version.current='';setDemoOverride(!demoOverride);setWindowIndex(0);setMethod(false);}} onClose={()=>setMethod(false)}/>}
  </main>;
}
function MethodDialog({recording,demoOverride,onDemo,onClose}:{recording:Recording;demoOverride:boolean;onDemo:()=>void;onClose:()=>void}) {
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{ref.current?.showModal();return()=>ref.current?.close();},[]);
  return <dialog ref={ref} className="method-dialog" onCancel={onClose} onClick={e=>{if(e.target===e.currentTarget)onClose();}}><div className="method-content"><button className="dialog-close" aria-label="Close methodology" onClick={onClose}><X size={20}/></button><div className="section-kicker"><Database size={14}/> HOW TO READ WORLDVIEW</div><h2>A recording of windows.<br/>A city of topics.</h2><p>Worldview samples public pages from different geographic locations. Each storefront is a topic. Each visitor represents one result appearing in a successful sample. Shop size reflects sampled prominence; visitor colors identify platforms.</p><p>Arrivals and departures compare the same country, profile, platform, surface, and query. Failed samples create gaps, never artificial departures. Animation spaces events within collection windows; it does not represent precise real-world arrival times.</p><p>Local views combine local language and regional settings. English controls keep queries and supported platform settings fixed. Comparisons use only shared successful surfaces. First seen means first detected within this recording, not the origin of a trend.</p><div className="method-status"><strong>{recording.mode==='demo'?'SYNTHETIC DEMONSTRATION':'PUBLISHED RECORDING'}</strong><p>{recording.mode==='demo'?'All topics, results, countries, and event patterns in this recording are illustrative. No geographic collection is claimed.':'These are collected observations. Proxy-dependent history remains dated after collection ends.'}</p></div><p className="mono">Cluster version: {recording.clusterVersion}<br/>Generated: {dateLabel(recording.generatedAt,true)} SGT<br/>Manifest checks: every 60 seconds</p><button className="primary-button" onClick={onDemo}>{demoOverride?'Return to published recording':'Open synthetic demonstration'}<ArrowRight size={15}/></button><button className="secondary-button" onClick={onClose}>Back to the city</button></div></dialog>;
}
