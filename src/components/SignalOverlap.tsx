'use client';
import { useState } from 'react';
import { ArrowUpRight, X } from 'lucide-react';
import { safeUrl } from '@/lib/recording';
import { VisualSignal } from '@/lib/signal-overlap';

const COLORS=['#e5bc88','#91bfe8','#d8a1d5','#9fd5b9','#b4b0ed','#e7b4a5','#acd1de','#d3cf96'];
export default function SignalOverlap({countries,signals,unit='link',onOpen}:{countries:{code:string;name:string}[];signals:VisualSignal[];unit?:'link'|'topic';onOpen?:(signal:VisualSignal)=>void}) {
  const [selected,setSelected]=useState<string|null>(null);
  const focused=signals.find(s=>s.id===selected);
  const shared=signals.filter(s=>s.present.length>1);
  const uncertain=signals.filter(s=>s.present.length===1&&s.unknown.length>0);
  function group(label:string,values:VisualSignal[],color:string,kind:string) {
    return <div className={`signal-group ${kind}`} style={{borderColor:`${color}55`}} key={label}>
      <div className="signal-group-heading"><span><i style={{background:color}}/>{label}</span><strong>{values.length}</strong></div>
      <div className="signal-dots">{values.map(s=><button key={s.id} className={`signal-dot ${focused?.id===s.id?'selected':''}`} style={{color}} aria-label={`${s.label} · ${s.present.join(' and ')}${s.unknown.length?' · incomplete comparison':''}`} aria-pressed={focused?.id===s.id} title={`${s.label}\nObserved: ${s.present.join(', ')}`} onClick={()=>setSelected(s.id)}><i style={s.present.length>1?{background:`conic-gradient(${s.present.map((c,index)=>`${COLORS[Math.max(0,countries.findIndex(country=>country.code===c))%COLORS.length]} ${index/s.present.length*100}% ${(index+1)/s.present.length*100}%`).join(',')})`,width:Math.min(18,10+s.present.length*2),height:Math.min(18,10+s.present.length*2)}:undefined}/></button>)}{!values.length&&<span className="signal-none">{countries.length<2?'Add another viewpoint to find overlap.':'None observed'}</span>}</div>
    </div>;
  }
  return <section className="signal-overlap" aria-label="Visual signal overlap">
    <div className="signal-heading"><div><span className="section-kicker">SHARED & DISTINCT</span><h4>{unit==='link'?'The same links. Different windows.':'What connects these viewpoints?'}</h4></div><span className="signal-dot-key"><i/>One dot = one {unit}</span></div>
    <div className="signal-shared-band">{group('Shared across viewpoints',shared,'#d9edaf','shared')}</div>
    <div className="signal-country-groups">{countries.map((c,index)=>group(countries.length<2?`Observed from ${c.code}`:`Only observed in ${c.code}`,signals.filter(s=>s.present.length===1&&s.present[0]===c.code&&!s.unknown.length),COLORS[index%COLORS.length],'distinct'))}</div>
    {uncertain.length>0&&group('Coverage differs · overlap unknown',uncertain,'#98a294','uncertain')}
    {focused?<div className="signal-inspector"><button className="signal-close" aria-label="Clear selected signal" onClick={()=>setSelected(null)}><X size={13}/></button><strong>{focused.label}</strong><div className="signal-presence">{countries.map((c,index)=>{const present=focused.present.includes(c.code),unknown=focused.unknown.includes(c.code);return <span key={c.code} className={present?'present':unknown?'unknown':'absent'}><i style={{background:present?COLORS[index%COLORS.length]:undefined}}/>{c.code}<small>{present?`#${focused.ranks[c.code]}`:unknown?'Coverage gap':'Not in sample'}</small></span>;})}</div>{onOpen?<button className="signal-open" onClick={()=>onOpen(focused)}>Explore this topic <ArrowUpRight size={12}/></button>:focused.url&&safeUrl(focused.url)?<a className="signal-open" href={safeUrl(focused.url)!} target="_blank" rel="noopener noreferrer">Open source <ArrowUpRight size={12}/></a>:null}</div>:<p className="signal-help">Multicolor dots are shared. Click a dot to see the {unit} and its position in each viewpoint. Hollow markers mean not found in a matching sample; gaps mean collection was unavailable.</p>}
  </section>;
}
