'use client';
import { useState } from 'react';
import { LoaderCircle, Languages } from 'lucide-react';
import { Item } from '@/lib/recording';
import { hasLocalScanService, scanApi } from '@/lib/scans';

const LANGUAGES:Record<string,string>={de:'German',es:'Spanish',fr:'French',hi:'Hindi',id:'Indonesian',ja:'Japanese',ko:'Korean',pt:'Portuguese',sv:'Swedish',zh:'Chinese'};

export default function TranslateHeadline({item,translation}:{item:Item;translation?:string}) {
  const language=item.language.toLowerCase().split('-')[0];
  const [english,setEnglish]=useState(''),[loading,setLoading]=useState(false),[error,setError]=useState('');
  if(!LANGUAGES[language]||!hasLocalScanService())return null;
  const translated=translation||english;
  async function translate() {
    if(loading||translated)return;
    setLoading(true);setError('');
    try {
      const response=await fetch(`${scanApi()}/api/translate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language,texts:[item.title]})});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error??'Translation unavailable.');
      setEnglish(data.translations?.[0]?.english??'');
    } catch(e) {setError(e instanceof Error?e.message:'Translation unavailable.');}
    finally {setLoading(false);}
  }
  return <div className="headline-translation">
    {!translated&&<button className="translate-button" onClick={()=>void translate()} disabled={loading} aria-label={`Translate ${LANGUAGES[language]} headline to English`}>
      {loading?<LoaderCircle className="spin" size={11}/>:<Languages size={11}/>} {loading?'Translating…':'Translate to English'}
    </button>}
    {loading&&<small className="translation-model-note">First use may download the pinned model; the original stays visible.</small>}
    {translated&&<p className="translated-headline"><strong>English translation</strong>{translated}<small>Local machine translation · original headline kept above</small></p>}
    {error&&<small className="translation-error" role="status">{error}</small>}
  </div>;
}
