import { PLATFORMS, Profile, Recording, Source, snapshotAt, success } from '@/lib/recording';

export default function CoveragePanel({recording,window,country,profile,onChoose}:{recording:Recording;window:string;country:string;profile:Profile;onChoose:(country:string,profile:Profile,source:Source)=>void}) {
  const available=(code:string,p:Profile)=>snapshotAt(recording,code,window,p)?.coverage.filter(c=>success(c.status))??[];
  const current=available(country,profile),alternateProfile=profile==='local'?'english':'local';
  const alternative=available(country,alternateProfile).filter(c=>!current.some(v=>v.source===c.source));
  return <div className="source-coverage">
    {alternative.length>0&&<p>Also recorded in {alternateProfile==='english'?'English control':'Local view'}: {[...new Set(alternative.map(c=>c.source))].map(source=><button key={source} onClick={()=>onChoose(country,alternateProfile,source)}>{PLATFORMS.find(p=>p.id===source)?.label}</button>)}</p>}
    <details><summary>Source coverage across countries</summary><p>Counts are sampled appearances. Profiles remain separate. “Not sampled” means no collection was attempted in this window.</p>
      <div className="coverage-countries">{recording.countries.map(c=><section key={c.code}><h4>{c.flag} {c.name}</h4>{(['local','english'] as Profile[]).map(p=>{
        const sample=snapshotAt(recording,c.code,window,p);
        return <div key={p}><strong>{p==='local'?'Local':'English'}</strong>{!sample?.coverage.length?<span>Not sampled</span>:PLATFORMS.filter(s=>sample.coverage.some(v=>v.source===s.id)).map(s=>{
          const observations=sample.coverage.filter(v=>v.source===s.id),ok=observations.filter(v=>success(v.status));
          return <button key={s.id} onClick={()=>onChoose(c.code,p,s.id)}>{s.label}: {ok.length?ok.reduce((n,v)=>n+v.itemCount,0):'failed'}{ok.length&&ok.length<observations.length?' · partial':''}</button>;
        })}</div>;
      })}</section>)}</div>
    </details>
  </div>;
}
