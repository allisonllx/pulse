'use client';
import { useCallback, useEffect, useState } from 'react';
type Entry={original:string;sourceLanguage:string;english:string;status:string};
export function useTranslations(version:string|undefined) {
  const [enabled,setEnabled]=useState(true),[entries,setEntries]=useState(new Map<string,string>());
  const [unsupported,setUnsupported]=useState<string[]>([]),[loaded,setLoaded]=useState(false);
  useEffect(()=>{
    let active=true;
    const load=()=>fetch('/data/translations.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(data=>{
      if(!active)return;
      if(data?.schemaVersion===1&&Array.isArray(data.entries)) {
        setEntries(new Map(data.entries.filter((e:Entry)=>e.status==='translated'&&typeof e.original==='string'&&typeof e.english==='string').map((e:Entry)=>[e.original,e.english])));
        setUnsupported(data.unsupportedLanguages??[]);
      }
      setLoaded(true);
    }).catch(()=>{if(active)setLoaded(true);});
    load(); const timer=setInterval(load,60000);
    return()=>{active=false;clearInterval(timer);};
  },[version]);
  const text=useCallback((original:string)=>enabled?(entries.get(original)??original):original,[enabled,entries]);
  return {enabled,setEnabled,text,entries,unsupported,loaded};
}
