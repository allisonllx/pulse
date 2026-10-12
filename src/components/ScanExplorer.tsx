'use client';
import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Globe2, LoaderCircle, RefreshCw, Search, X } from 'lucide-react';
import { dateLabel, readRecording, Recording, safeUrl, coverageKey } from '@/lib/recording';
import { Scan, scanApi, SCAN_COUNTRIES, scanItems, ScanSummary, sortScanItems, STARTER_TOPICS } from '@/lib/scans';
import SignalOverlap from './SignalOverlap';
import { scanSignals } from '@/lib/signal-overlap';
import { MARKET_CONCEPTS, CONCEPT_COUNTRIES, conceptMatrix, queryTerm } from '@/lib/concepts';
import ConceptPatterns from './ConceptPatterns';

export default function ScanExplorer({onRecording,onExit}:{onRecording:(recording:Recording)=>void;onExit:()=>void}) {
  const [keyword,setKeyword]=useState(''), [countries,setCountries]=useState(['SG','US','GB','JP']);
  const [catalog,setCatalog]=useState<ScanSummary[]>([]), [scan,setScan]=useState<Scan|null>(null);
  const [busy,setBusy]=useState(false), [error,setError]=useState(''), [cached,setCached]=useState(false);
  const [platform,setPlatform]=useState('all'), [location,setLocation]=useState('all'), [order,setOrder]=useState<'relevance'|'rank'|'freshness'>('relevance');
  const [conceptId,setConceptId]=useState(''), [vertical,setVertical]=useState('all'), [term,setTerm]=useState('');
  const concept=MARKET_CONCEPTS.find(c=>c.id===conceptId);
  const [expanded,setExpanded]=useState(false);
  const controller=useRef<AbortController|null>(null), generation=useRef(0);
  const update=useCallback((value:Scan)=>{
    setScan(value);
    if(value.recording)onRecording(readRecording(value.recording));
  },[onRecording]);
  const loadCatalog=useCallback(async()=>{
    try {const r=await fetch('/data/scans/index.json',{cache:'no-store'});if(r.ok)setCatalog(await r.json() as ScanSummary[]);}catch {/* Cached recommendations are optional. */}
  },[]);
  useEffect(()=>{
    const id=new URLSearchParams(window.location.search).get('scan');
    if(!id||!/^[a-f0-9]{24}$/.test(id))return;
    const abort=new AbortController();
    void (async()=>{
      try {
        const response=await fetch(`/data/scans/${id}.json`,{cache:'no-store',signal:abort.signal});
        if(!response.ok)throw new Error('That scan is unavailable.');
        const saved=await response.json() as Scan;
        setKeyword(saved.keyword);setCountries(saved.countries);setConceptId(saved.concept?.id??'');setExpanded(true);
        setBusy(['queued','running'].includes(saved.status));setCached(!['queued','running'].includes(saved.status));update(saved);
      }catch(error){if(!abort.signal.aborted)setError(error instanceof Error?error.message:'Could not open this scan.');}
    })();
    return()=>abort.abort();
  },[update]);
  useEffect(()=>{void loadCatalog();return()=>{generation.current++;controller.current?.abort();};},[loadCatalog]);
  useEffect(()=>{
    if(!scan||!['queued','running'].includes(scan.status))return;
    let active=true;
    const abort=new AbortController();
    const timer=setInterval(async()=>{
      try {
        const r=await fetch(`${scanApi()}/api/scans/${scan.id}`,{cache:'no-store',signal:abort.signal});
        if(!r.ok)throw new Error('Scan progress is unavailable.');
        const value=await r.json() as Scan;
        if(active){update(value);setError('');if(!['queued','running'].includes(value.status)){setBusy(false);void loadCatalog();}}
      }catch(e){if(active&&!(e instanceof Error&&e.name==='AbortError')){setError('Connection interrupted. Collected findings remain visible; retrying progress…');}}
    },1500);
    return()=>{active=false;abort.abort();clearInterval(timer);};
  },[scan?.id,scan?.status,update,loadCatalog]);

  async function start(value=keyword,refresh=false,summary?:ScanSummary,selectedConcept=conceptId,selectedCountries=countries) {
    if(!value.trim()||busy)return;
    const run=++generation.current;
    controller.current?.abort();const abort=new AbortController();controller.current=abort;
    setKeyword(value);setCountries(selectedCountries);setBusy(true);setError('');setExpanded(true);setPlatform('all');setLocation('all');setTerm('');setConceptId(selectedConcept);
    try {
      if(summary&&!refresh) {
        const r=await fetch(`/data/scans/${summary.id}.json`,{signal:abort.signal});
        if(!r.ok)throw new Error('That snapshot is unavailable. Refresh it with a live scan.');
        const saved=await r.json() as Scan;
        if(generation.current===run){setCountries(saved.countries);setConceptId(saved.concept?.id??'');setCached(true);update(saved);setBusy(false);}return;
      }
      const r=await fetch(`${scanApi()}/api/scans`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword:value,countries:selectedCountries,refresh,...(selectedConcept?{conceptId:selectedConcept}:{})}),signal:abort.signal});
      if(r.status===404||!r.headers.get('content-type')?.includes('application/json'))throw new Error('Live collection is unavailable here. Open a saved snapshot or connect the scan service.');
      const data=await r.json();
      if(!r.ok)throw new Error(data.error??'Could not start this scan.');
      if(generation.current===run){setCached(data.cached);update(data.scan);setBusy(['queued','running'].includes(data.scan.status));}
    }catch(e){if(generation.current===run){setBusy(false);setError(e instanceof TypeError?'Live collection is unavailable here. Start the local scan service to search, or open a saved snapshot.':e instanceof Error?e.message:'Could not open the scan.');}}
  }
  function submit(e:FormEvent){e.preventDefault();const saved=catalog.find(s=>(conceptId?s.conceptId===conceptId:!s.conceptId&&s.keyword.toLowerCase()===keyword.trim().toLowerCase())&&[...s.countries].sort().join() === [...countries].sort().join());void start(keyword,false,saved);}
  const items=scan?scanItems(scan):[];
  const comparableKeys=term&&scan?new Set(conceptMatrix(scan,platform).find(r=>r.alias.term===term)?.commonKeys??[]):null;
  const visible=sortScanItems(items.filter(i=>(platform==='all'||i.discovery?.platform===platform)&&(location==='all'||i.country===location)&&(!term||(queryTerm(i.query)===queryTerm(term)&&comparableKeys?.has(coverageKey(i))))),order);
  const maxCount=Math.max(1,...(scan?.countries??[]).map(c=>items.filter(i=>i.country===c).length));
  return <section className="scan-explorer" aria-label="Search the world">
    <div className="scan-intro"><span className="section-kicker"><Globe2 size={14}/> SEARCH FROM EVERYWHERE</span><h2>What does the world see?</h2><p>Explore what could travel between markets—and what needs local adaptation.</p></div>
    <div className="concept-library"><div className="concept-library-heading"><span className="section-kicker">EXPLORE CROSS-MARKET IDEAS</span><label>Vertical<select aria-label="Concept vertical" value={vertical} onChange={e=>setVertical(e.target.value)}><option value="all">All verticals</option>{[...new Set(MARKET_CONCEPTS.map(c=>c.vertical))].map(v=><option key={v}>{v}</option>)}</select></label></div><div className="concept-cards">{MARKET_CONCEPTS.filter(c=>vertical==='all'||c.vertical===vertical).map(c=><button key={c.id} disabled={busy} aria-pressed={conceptId===c.id} onClick={()=>{setConceptId(c.id);setKeyword(c.label);setCountries([...CONCEPT_COUNTRIES]);}}><small>{c.vertical}{catalog.some(s=>s.conceptId===c.id)?' · Snapshot':''}</small><strong>{c.label}</strong><span>{c.aliases.map(a=>a.term).join(' · ')}</span></button>)}</div>{concept&&<div className="concept-selection"><strong>{concept.label}</strong><p>{concept.question}</p><div>{concept.aliases.map(a=><span key={a.term}>{a.term}</span>)}</div><small>3 terms per market · 13 signals per country · select viewpoints below</small><button disabled={busy} onClick={()=>{setConceptId('');setKeyword('');}}>Use a single keyword</button></div>}</div>
    <form className="scan-form" onSubmit={submit}><label className="scan-input"><Search size={18}/><input aria-label="Keyword to scan" placeholder="Try Claude Code, Labubu, or anything…" value={keyword} onChange={e=>{setKeyword(e.target.value);setConceptId('');}} maxLength={100} required/></label><button className="primary-button" disabled={busy||!keyword.trim()}>{busy?<LoaderCircle className="spin" size={16}/>:<Globe2 size={16}/>} {busy?'Scanning…':concept?'Explore concept':'Explore the world'}</button></form>
    <div className="scan-recommendations"><span>EXPLORE</span>{STARTER_TOPICS.map(topic=>{const saved=catalog.find(s=>s.keyword.toLowerCase()===topic.toLowerCase());return <button key={topic} disabled={busy} onClick={()=>void start(topic,false,saved,'')}>{topic} <small>{saved?'Snapshot':'Live scan'}</small></button>;})}{catalog.filter(s=>!STARTER_TOPICS.some(t=>t.toLowerCase()===s.keyword.toLowerCase())).slice(0,3).map(s=><button key={s.id} disabled={busy} onClick={()=>void start(s.keyword,false,s,s.conceptId??'')}>{s.keyword} <small>Snapshot</small></button>)}</div>
    <details className="scan-settings"><summary>Viewpoints · {countries.join(' / ')} · {concept?'13':'7'} signals per country</summary><div>{SCAN_COUNTRIES.map(([code,name])=><label key={code}><input type="checkbox" checked={countries.includes(code)} disabled={busy||(countries.length===1&&countries.includes(code))} onChange={e=>setCountries(cs=>e.target.checked?[...cs,code]:cs.filter(c=>c!==code))}/>{name}</label>)}</div><p>Queries stay fixed across markets; concept bundles include their listed language variants. Residential IP varies; News also uses each country’s edition. Social discovery searches indexed public links.</p></details>
    {error&&<p className="scan-error" role="status">{error}</p>}
    {scan&&<div className="scan-result">
      <div className="scan-result-heading"><div><span className="section-kicker">{cached?'SNAPSHOT':busy?'LIVE COLLECTION':'SAVED SCAN'} · {dateLabel(scan.createdAt)} SGT</span><h3>{scan.keyword}</h3></div><span className="scan-outcome">{scan.status} · {scan.completed}/{scan.planned} signals</span><button aria-label="Refresh scan live" disabled={busy} onClick={()=>void start(scan.keyword,true,undefined,scan.concept?.id??'',scan.countries)}><RefreshCw size={17}/></button><button aria-label="Close scan" disabled={busy} onClick={()=>{setScan(null);setExpanded(false);onExit();}}><X size={17}/></button></div>
      <progress aria-label="Scan progress" max={scan.planned||1} value={scan.completed}/>
      {busy&&<p className="scan-active" role="status"><LoaderCircle className="spin" size={13}/>{scan.active?`${scan.active.country} · ${scan.active.source} · ${scan.active.query}`:'Deploying geographic observers…'}</p>}
      {scan.error&&<p className="scan-error">{scan.error}</p>}
      <div className="scan-world">{scan.countries.map(c=>{const count=items.filter(i=>i.country===c).length;const events=scan.events.filter(e=>e.country===c);const active=busy&&scan.active?.country===c;return <button className={`${active?'collecting':''} ${location===c?'selected':''}`} key={c} onClick={()=>setLocation(location===c?'all':c)}><span>{SCAN_COUNTRIES.find(([code])=>code===c)?.[1]??c}<small>{active?'Collecting…':events.length?`${events.filter(e=>e.status==='success').length} successful fetches`:'Waiting'}</small></span><strong>{count}</strong><i style={{width:`${count/maxCount*100}%`}}/></button>;})}</div>
      <p className="scan-method">Bars compare accepted results in these samples. Search rank and visible engagement labels do not measure regional popularity. Missing or blocked searches stay visible.</p>
      <ConceptPatterns scan={scan} platform={platform} onSelect={(value,country)=>{setTerm(value);setLocation(country);setExpanded(true);}}/>
      <SignalOverlap countries={scan.countries.map(code=>({code,name:SCAN_COUNTRIES.find(([c])=>c===code)?.[1]??code}))} signals={scanSignals(scan,platform)}/>
      <button className="scan-disclosure" onClick={()=>setExpanded(!expanded)}>{expanded?'Hide':'Show'} findings and collection steps · {items.length} results</button>
      {expanded&&<><div className="scan-filters"><label>Source<select aria-label="Scan platform" value={platform} onChange={e=>setPlatform(e.target.value)}>{['all','web','news','video','instagram','tiktok','x','reddit'].map(p=><option key={p} value={p}>{p==='all'?'All sources':p==='x'?'X':p}</option>)}</select></label><label>Order<select aria-label="Scan result order" value={order} onChange={e=>setOrder(e.target.value as typeof order)}><option value="relevance">Keyword relevance</option><option value="rank">Search result rank</option><option value="freshness">Has freshness evidence</option></select></label>{term&&<button onClick={()=>setTerm('')}>Clear term: {term}</button>}<button onClick={()=>setLocation('all')}>{location==='all'?'All viewpoints':`Clear ${location} filter`}</button></div>
      <div className="scan-findings">{visible.slice(0,30).map(i=><article key={`${i.country}-${i.observationId}-${i.id}`}><span className="section-kicker">{i.country} · {i.discovery?.platform} · #{i.rank} via {i.source}</span>{safeUrl(i.url)?<a href={safeUrl(i.url)!} target="_blank" rel="noopener noreferrer">{i.title}<ArrowUpRight size={13}/></a>:<span>{i.title}</span>}<p>{i.snippet}</p><div className="scan-evidence-labels"><span>Relevance {Math.round((i.discovery?.relevance??0)*100)}%</span>{i.discovery?.freshnessLabel&&<span>{i.discovery.freshnessLabel}</span>}{i.discovery?.engagementLabels.map((m,index)=><span key={index}>{m} · snippet</span>)}</div><small>Query: {i.query}</small></article>)}</div>
      {!visible.length&&<p className="scan-method">{busy?'Findings will appear as each source returns.':'No accepted results for these filters. Inspect the collection steps for failed sources.'}</p>}
      <details className="scan-log"><summary>Collection steps · {scan.events.length} fetches</summary><ol>{scan.events.map((e,index)=><li key={index}><span>{e.country} · {e.channel} · {e.source}{e.fallback?' fallback':''}</span><strong>{e.status==='success'?`${e.itemCount} results`:(e.error??e.status).replaceAll('_',' ')}</strong><small>{e.query}</small></li>)}</ol></details></>}
    </div>}
  </section>;
}
