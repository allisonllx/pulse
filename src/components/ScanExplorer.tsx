'use client';
import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Globe2, LoaderCircle, RefreshCw, Search, X } from 'lucide-react';
import { dateLabel, readRecording, Recording, safeUrl, coverageKey } from '@/lib/recording';
import { hasLocalScanService, Scan, scanApi, SCAN_COUNTRIES, scanItems, ScanSummary, sortScanItems, STARTER_TOPICS } from '@/lib/scans';
import SignalOverlap from './SignalOverlap';
import { scanSignals } from '@/lib/signal-overlap';
import { MARKET_CONCEPTS, CONCEPT_COUNTRIES, conceptMatrix, queryTerm } from '@/lib/concepts';
import ConceptPatterns from './ConceptPatterns';
import TranslateHeadline from './TranslateHeadline';

export default function ScanExplorer({onRecording,onExit}:{onRecording:(recording:Recording)=>void;onExit:()=>void}) {
  const [keyword,setKeyword]=useState(''), [countries,setCountries]=useState(['SG','US','GB','JP']);
  const [queryLanguage,setQueryLanguage]=useState('en');
  const [catalog,setCatalog]=useState<ScanSummary[]>([]), [scan,setScan]=useState<Scan|null>(null);
  const [busy,setBusy]=useState(false), [error,setError]=useState(''), [cached,setCached]=useState(false);
  const [platform,setPlatform]=useState('all'), [location,setLocation]=useState('all'), [order,setOrder]=useState<'relevance'|'rank'|'freshness'>('relevance');
  const [conceptId,setConceptId]=useState(''), [vertical,setVertical]=useState('all'), [term,setTerm]=useState('');
  const [translatedHeadlines,setTranslatedHeadlines]=useState<Record<string,string>>({}),[translating,setTranslating]=useState(false),[translationMessage,setTranslationMessage]=useState('');
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
        setKeyword(saved.keyword);setCountries(saved.countries);setConceptId(saved.concept?.id??'');setQueryLanguage(saved.queryLanguage??'en');setExpanded(true);
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

  async function start(value=keyword,refresh=false,summary?:ScanSummary,selectedConcept=conceptId,selectedCountries=countries,selectedLanguage=queryLanguage) {
    if(!value.trim()||busy)return;
    const run=++generation.current;
    controller.current?.abort();const abort=new AbortController();controller.current=abort;
    const language=selectedConcept?'en':selectedLanguage;
    setKeyword(value);setCountries(selectedCountries);setQueryLanguage(language);setBusy(true);setError('');setExpanded(true);setPlatform('all');setLocation('all');setTerm('');setConceptId(selectedConcept);setTranslatedHeadlines({});setTranslationMessage('');
    try {
      if(summary&&!refresh) {
        const r=await fetch(`/data/scans/${summary.id}.json`,{signal:abort.signal});
        if(!r.ok)throw new Error('That snapshot is unavailable. Refresh it with a live scan.');
        const saved=await r.json() as Scan;
        if(generation.current===run){setCountries(saved.countries);setConceptId(saved.concept?.id??'');setQueryLanguage(saved.queryLanguage??'en');setCached(true);update(saved);setBusy(false);}return;
      }
      const r=await fetch(`${scanApi()}/api/scans`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword:value,countries:selectedCountries,queryLanguage:language,refresh,...(selectedConcept?{conceptId:selectedConcept}:{})}),signal:abort.signal});
      if(r.status===404||!r.headers.get('content-type')?.includes('application/json'))throw new Error('Live collection is unavailable here. Open a saved snapshot or connect the scan service.');
      const data=await r.json();
      if(!r.ok)throw new Error(data.error??'Could not start this scan.');
      if(generation.current===run){setCached(data.cached);update(data.scan);setBusy(['queued','running'].includes(data.scan.status));}
    }catch(e){if(generation.current===run){setBusy(false);setError(e instanceof TypeError?'Live collection is unavailable here. Start the local scan service to search, or open a saved snapshot.':e instanceof Error?e.message:'Could not open the scan.');}}
  }
  function submit(e:FormEvent){e.preventDefault();const language=conceptId?'en':queryLanguage;const saved=catalog.find(s=>(conceptId?s.conceptId===conceptId:!s.conceptId&&s.keyword.toLowerCase()===keyword.trim().toLowerCase())&&(s.queryLanguage??'en')===language&&[...s.countries].sort().join() === [...countries].sort().join());void start(keyword,false,saved,conceptId,countries,language);}
  function scanItemKey(i:{country:string;observationId:string;id:string}){return `${i.country}-${i.observationId}-${i.id}`;}
  async function translateVisibleHeadlines(){
    const candidates=visible.slice(0,30).filter(i=>i.language&&i.language.toLowerCase().split('-')[0]!=='en');
    if(!candidates.length||translating)return;
    const groups=new Map<string,typeof candidates>();
    for(const item of candidates){const language=item.language.toLowerCase().split('-')[0];groups.set(language,[...(groups.get(language)??[]),item]);}
    setTranslating(true);setTranslationMessage('First use may download a pinned model; originals stay visible.');
    let total=0;
    try{
      const additions:Record<string,string>={};
      for(const [language,itemsForLanguage] of groups){
        for(let offset=0;offset<itemsForLanguage.length;offset+=20){
          const batch=itemsForLanguage.slice(offset,offset+20);
          const response=await fetch(`${scanApi()}/api/translate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language,texts:batch.map(i=>i.title)})});
          const data=await response.json();if(!response.ok)throw new Error(data.error??'Translation unavailable.');
          for(let index=0;index<batch.length;index++){const english=data.translations?.[index]?.english;if(english){additions[scanItemKey(batch[index])]=english;total++;}}
        }
      }
      setTranslatedHeadlines(current=>({...current,...additions}));setTranslationMessage(`Translated ${total} headlines locally; originals are preserved.`);
    }catch(error){setTranslationMessage(error instanceof Error?error.message:'Translation unavailable.');}
    finally{setTranslating(false);}
  }
  const items=scan?scanItems(scan):[];
  const comparableKeys=term&&scan?new Set(conceptMatrix(scan,platform).find(r=>r.alias.term===term)?.commonKeys??[]):null;
  const visible=sortScanItems(items.filter(i=>(platform==='all'||i.discovery?.platform===platform)&&(location==='all'||i.country===location)&&(!term||(queryTerm(i.query)===queryTerm(term)&&comparableKeys?.has(coverageKey(i))))),order);
  const maxCount=Math.max(1,...(scan?.countries??[]).map(c=>items.filter(i=>i.country===c).length));
  return <section className="scan-explorer" aria-label="Search the world">
    <div className="scan-intro"><span className="section-kicker"><Globe2 size={14}/> SEARCH FROM EVERYWHERE</span><h2>What does the world see?</h2><p>Explore what could travel between markets—and what needs local adaptation.</p></div>
    <div className="concept-library"><div className="concept-library-heading"><span className="section-kicker">EXPLORE CROSS-MARKET IDEAS</span><label>Vertical<select aria-label="Concept vertical" value={vertical} onChange={e=>setVertical(e.target.value)}><option value="all">All verticals</option>{[...new Set(MARKET_CONCEPTS.map(c=>c.vertical))].map(v=><option key={v}>{v}</option>)}</select></label></div><div className="concept-cards">{MARKET_CONCEPTS.filter(c=>vertical==='all'||c.vertical===vertical).map(c=><button key={c.id} disabled={busy} aria-pressed={conceptId===c.id} onClick={()=>{setConceptId(c.id);setKeyword(c.label);setCountries([...CONCEPT_COUNTRIES]);}}><small>{c.vertical}{catalog.some(s=>s.conceptId===c.id)?' · Snapshot':''}</small><strong>{c.label}</strong><span>{c.aliases.map(a=>a.term).join(' · ')}</span></button>)}</div>{concept&&<div className="concept-selection"><strong>{concept.label}</strong><p>{concept.question}</p><div>{concept.aliases.map(a=><span key={a.term}>{a.term}</span>)}</div>{concept.marketTerms&&<small className="concept-local-terms">Local search terms: {Object.entries(concept.marketTerms).map(([country,terms])=>`${country}: ${(terms??[]).join(', ')}`).join(' · ')}</small>}<small>English controls plus curated local-language terms where available · select viewpoints below</small><button disabled={busy} onClick={()=>{setConceptId('');setKeyword('');}}>Use a single keyword</button></div>}</div>
    <form className="scan-form" onSubmit={submit}><label className="scan-input"><Search size={18}/><input aria-label="Keyword to scan" placeholder="Try Claude Code, Labubu, or anything…" value={keyword} onChange={e=>{setKeyword(e.target.value);setConceptId('');}} maxLength={100} required/></label><label className="query-language">Query language<select aria-label="Search language" value={queryLanguage} disabled={busy||Boolean(concept)} onChange={e=>setQueryLanguage(e.target.value)}><option value="en">English control</option><option value="de">German</option><option value="es">Spanish</option><option value="fr">French</option><option value="hi">Hindi</option><option value="id">Indonesian</option><option value="ja">Japanese</option><option value="ko">Korean</option><option value="pt">Portuguese</option><option value="sv">Swedish</option><option value="zh">Chinese</option></select></label><button className="primary-button" disabled={busy||!keyword.trim()}>{busy?<LoaderCircle className="spin" size={16}/>:<Globe2 size={16}/>} {busy?'Scanning…':concept?'Explore concept':'Explore the world'}</button><small className="query-language-note">The exact phrase is searched with this language setting across every selected country. Use a matching native-language phrase for local discovery.</small></form>
    <div className="scan-recommendations"><span>EXPLORE</span>{STARTER_TOPICS.map(topic=>{const saved=catalog.find(s=>s.keyword.toLowerCase()===topic.toLowerCase());return <button key={topic} disabled={busy} onClick={()=>void start(topic,false,saved,'')}>{topic} <small>{saved?'Snapshot':'Live scan'}</small></button>;})}{catalog.filter(s=>!STARTER_TOPICS.some(t=>t.toLowerCase()===s.keyword.toLowerCase())).slice(0,3).map(s=><button key={s.id} disabled={busy} onClick={()=>void start(s.keyword,false,s,s.conceptId??'')}>{s.keyword} <small>Snapshot</small></button>)}</div>
    <details className="scan-settings"><summary>Viewpoints · {countries.join(' / ')} · {countries.map(code=>concept?13+(concept.marketTerms?.[code]?.length??0)*2:7).join(' / ')} signals per country</summary><div>{SCAN_COUNTRIES.map(([code,name])=><label key={code}><input type="checkbox" checked={countries.includes(code)} disabled={busy||(countries.length===1&&countries.includes(code))} onChange={e=>setCountries(cs=>e.target.checked?[...cs,code]:cs.filter(c=>c!==code))}/>{name}</label>)}</div><p>Concept bundles keep English control queries and add curated Japanese or Korean terms only in those markets. For free text, choose a search language and enter the phrase in that language; the same phrase is compared across selected countries with country-edition News and region settings. Missing or failed queries remain coverage gaps. Social discovery searches indexed public links.</p></details>
    {error&&<p className="scan-error" role="status">{error}</p>}
    {scan&&<div className="scan-result">
      <div className="scan-result-heading"><div><span className="section-kicker">{cached?'SNAPSHOT':busy?'LIVE COLLECTION':'SAVED SCAN'} · {dateLabel(scan.createdAt)} SGT</span><h3>{scan.keyword}</h3><small className="scan-language-label">{scan.concept?'English controls + localized additions':scan.queryLanguage&&scan.queryLanguage!=='en'?`Search language: ${scan.queryLanguage} · local-context sample`:'English control query'}</small></div><span className="scan-outcome">{scan.status} · {scan.completed}/{scan.planned} signals</span><button aria-label="Refresh scan live" disabled={busy} onClick={()=>void start(scan.keyword,true,undefined,scan.concept?.id??'',scan.countries,scan.queryLanguage??'en')}><RefreshCw size={17}/></button><button aria-label="Close scan" disabled={busy} onClick={()=>{setScan(null);setExpanded(false);onExit();}}><X size={17}/></button></div>
      <progress aria-label="Scan progress" max={scan.planned||1} value={scan.completed}/>
      {busy&&<p className="scan-active" role="status"><LoaderCircle className="spin" size={13}/>{scan.active?`${scan.active.country} · ${scan.active.source} · ${scan.active.query}`:'Deploying geographic observers…'}</p>}
      {scan.error&&<p className="scan-error">{scan.error}</p>}
      <div className="scan-world">{scan.countries.map(c=>{const count=items.filter(i=>i.country===c).length;const events=scan.events.filter(e=>e.country===c);const active=busy&&scan.active?.country===c;return <button className={`${active?'collecting':''} ${location===c?'selected':''}`} key={c} onClick={()=>setLocation(location===c?'all':c)}><span>{SCAN_COUNTRIES.find(([code])=>code===c)?.[1]??c}<small>{active?'Collecting…':events.length?`${events.filter(e=>e.status==='success').length} successful fetches`:'Waiting'}</small></span><strong>{count}</strong><i style={{width:`${count/maxCount*100}%`}}/></button>;})}</div>
      <p className="scan-method">Bars compare accepted results in these samples. Search rank and visible engagement labels do not measure regional popularity. Missing or blocked searches stay visible.</p>
      <ConceptPatterns scan={scan} platform={platform} onSelect={(value,country)=>{setTerm(value);setLocation(country);setExpanded(true);}}/>
      <SignalOverlap countries={scan.countries.map(code=>({code,name:SCAN_COUNTRIES.find(([c])=>c===code)?.[1]??code}))} signals={scanSignals(scan,platform)}/>
      <button className="scan-disclosure" onClick={()=>setExpanded(!expanded)}>{expanded?'Hide':'Show'} findings and collection steps · {items.length} results</button>
      {expanded&&<><div className="scan-filters"><label>Source<select aria-label="Scan platform" value={platform} onChange={e=>setPlatform(e.target.value)}>{['all','web','news','video','instagram','tiktok','x','reddit'].map(p=><option key={p} value={p}>{p==='all'?'All sources':p==='x'?'X':p}</option>)}</select></label><label>Order<select aria-label="Scan result order" value={order} onChange={e=>setOrder(e.target.value as typeof order)}><option value="relevance">Keyword relevance</option><option value="rank">Search result rank</option><option value="freshness">Has freshness evidence</option></select></label>{term&&<button onClick={()=>setTerm('')}>Clear term: {term}</button>}<button onClick={()=>setLocation('all')}>{location==='all'?'All viewpoints':`Clear ${location} filter`}</button>{hasLocalScanService()&&visible.slice(0,30).some(i=>i.language&&i.language.toLowerCase().split('-')[0]!=='en')&&<button className="translate-visible" onClick={()=>void translateVisibleHeadlines()} disabled={translating}>{translating?'Translating…':'Translate visible headlines'}</button>}</div>{translationMessage&&<p className="translation-batch-status" role="status">{translationMessage}</p>}
      <div className="scan-findings">{visible.slice(0,30).map(i=><article key={`${i.country}-${i.observationId}-${i.id}`}><span className="section-kicker">{i.country} · {i.discovery?.platform} · #{i.rank} via {i.source}</span>{safeUrl(i.url)?<a href={safeUrl(i.url)!} target="_blank" rel="noopener noreferrer">{i.title}<ArrowUpRight size={13}/></a>:<span>{i.title}</span>}<TranslateHeadline item={i} translation={translatedHeadlines[scanItemKey(i)]}/><p>{i.snippet}</p><div className="scan-evidence-labels"><span>Relevance {Math.round((i.discovery?.relevance??0)*100)}%</span>{i.discovery?.freshnessLabel&&<span>{i.discovery.freshnessLabel}</span>}{i.discovery?.engagementLabels.map((m,index)=><span key={index}>{m} · snippet</span>)}</div><small>Query: {i.query}</small></article>)}</div>
      {!visible.length&&<p className="scan-method">{busy?'Findings will appear as each source returns.':'No accepted results for these filters. Inspect the collection steps for failed sources.'}</p>}
      <details className="scan-log"><summary>Collection steps · {scan.events.length} fetches</summary><ol>{scan.events.map((e,index)=><li key={index}><span>{e.country} · {e.channel} · {e.source}{e.profile==='local'?` · ${e.language} local`:''}{e.fallback?' fallback':''}</span><strong>{e.status==='success'?`${e.itemCount} results`:(e.error??e.status).replaceAll('_',' ')}</strong><small>{e.query}</small></li>)}</ol></details></>}
    </div>}
  </section>;
}
