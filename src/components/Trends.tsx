'use client';
import { useMemo, useState } from 'react';
import { dateLabel, Profile, Recording, Snapshot, Source, Topic } from '@/lib/recording';
import { knownTopics, rankedTrends, topicJourney } from '@/lib/trends';

export default function Trends({recording,snapshot,profile,source,window,ai,topicId,onTopic,onCountry,text}:{recording:Recording;snapshot:Snapshot|undefined;profile:Profile;source:Source|'all';window:string;ai:boolean;topicId:string|null;onTopic:(id:string)=>void;onCountry:(country:string,topic:string)=>void;text:(value:string)=>string}) {
  const [search,setSearch]=useState('');
  const all=useMemo(()=>knownTopics(recording,profile,source,window),[recording,profile,source,window]);
  const index=recording.windows.indexOf(window);
  const previous=recording.snapshots.find(s=>s.country===snapshot?.country&&s.profile===profile&&s.window===recording.windows[index-1]);
  const rankings=rankedTrends(snapshot,previous,source,ai);
  const displayable=all.filter(t=>!ai||t.category==='ai');
  const topic=displayable.find(t=>t.id===topicId)??rankings[0]?.topic;
  const journey=topic?topicJourney(recording,topic.id,profile,source,snapshot,window):null;
  const matching=displayable.filter(t=>`${text(t.label)} ${t.label} ${t.aliases.join(' ')}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="trends-view">
    <div className="trends-intro"><div className="section-kicker">OBSERVED TOPICS · {profile==='local'?'LOCAL VIEW':'ENGLISH CONTROL'}</div><h3>Follow a topic across windows.</h3><p>Clusters group related results. Prominence weights result rank within matching successful surfaces.</p></div>
    <label className="trend-search">Find a recorded topic<input aria-label="Find a recorded topic across countries" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Headline, name, or trend…"/></label>
    <div className="watched-topics">{displayable.filter(t=>t.category==='watch-query').map(t=><button key={t.id} onClick={()=>onTopic(t.id)}>{t.label}</button>)}</div>{search&&<div className="trend-search-results">{matching.slice(0,12).map(t=><button key={t.id} onClick={()=>{onTopic(t.id);setSearch('');}}>{text(t.label)}</button>)}{matching.length===0&&<p>No matching topic has been collected. Absence here does not mean no coverage on the internet.</p>}</div>}
    <div className="trend-ranking"><h4>Prominent clusters here</h4>{rankings.slice(0,8).map(({topic:t,count,share,delta})=><button className={t.id===topic?.id?'active':''} key={t.id} onClick={()=>onTopic(t.id)}><span>{text(t.label)}<small>{count} appearances · {(share*100).toFixed(1)}% rank-weighted prominence</small></span><b>{delta===null?'—':delta>0?`+${delta}`:String(delta)}</b></button>)}<p className="analysis-note">Change uses shared successful surfaces in consecutive six-hour windows. {index===0?'Only one window is available at this time; no temporal trend is inferred.':'Missing or failed samples break change comparisons.'}</p></div>
    {journey&&topic&&<section className="topic-journey"><div className="section-kicker">COUNTRY × COLLECTION WINDOW</div><h4>{text(topic.label)}</h4><p className="analysis-note">{journey.referenceSurfaces} fixed surface/query slots for this series. Numbers count appearances; — means unequal or missing coverage. * means observed in a partial sample. {topic.id==='watch:cornell 7'?'This series keeps results naming Cornell; unrelated query matches are excluded.':''}</p>
      <div className="journey-scroll"><table><thead><tr><th>Viewpoint</th>{journey.windows.map(w=><th key={w}>{dateLabel(w)}<small>SGT</small></th>)}</tr></thead><tbody>{journey.rows.map(row=><tr key={row.country.code}><th><button onClick={()=>onCountry(row.country.code,topic.id)}>{row.country.flag} {row.country.name}</button></th>{row.cells.map(c=><td key={c.window} title={c.share===null?'No comparable complete sample':`${(c.share*100).toFixed(1)}% rank-weighted prominence`} data-coverage={c.count===null?'gap':'complete'} style={{background:c.share===null?'transparent':`rgba(217,237,175,${Math.min(.55,c.share*2.5)})`}}>{c.count===null?(c.partial?'*':'—'):c.count}</td>)}</tr>)}</tbody></table></div>
      <h4>First detections in this recording</h4>{journey.detections.length===0&&<p className="analysis-note">No supporting result observed for this series yet.</p>}<ol className="detection-order">{journey.detections.map(row=><li key={row.country.code}><button onClick={()=>onCountry(row.country.code,topic.id)}>{row.country.flag} {row.country.name}</button><span>{dateLabel(row.firstAt!)} SGT</span></li>)}</ol><p className="analysis-note">Countries collected in the same window form a detection cohort. Timestamps reflect collection order; they do not establish where a topic originated or causal propagation.</p>
    </section>}
  </div>;
}
