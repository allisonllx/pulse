'use client';
import { Country } from '@/lib/recording';
const coords: Record<string, [number, number]> = { SG:[207,111], US:[64,62], GB:[132,43], JP:[239,66], IN:[191,88], BR:[99,136], SE:[150,34], DE:[146,51], FR:[136,57], KR:[232,71], ID:[220,124], MY:[205,106], AU:[239,151], CA:[66,39], MX:[64,87] };
export default function Atlas({ countries, selected, onSelect }: { countries: Country[]; selected: string; onSelect: (code: string) => void }) {
  return <svg viewBox="0 0 300 185" className="atlas" role="img" aria-label="Recording locations on a world map">
    <defs><radialGradient id="atlasGlow"><stop offset="0" stopColor="#638a72" stopOpacity=".25" /><stop offset="1" stopColor="#638a72" stopOpacity="0" /></radialGradient></defs>
    <ellipse cx="150" cy="94" rx="147" ry="88" fill="url(#atlasGlow)" />
    {[36,65,94,123,152].map(y=><path key={y} d={`M 12 ${y} Q 150 ${y+14} 288 ${y}`} stroke="#34433e" fill="none" strokeWidth=".5" />)}
    {[60,105,150,195,240].map(x=><ellipse key={x} cx="150" cy="94" rx={Math.abs(x-150)+12} ry="88" stroke="#34433e" fill="none" strokeWidth=".5" />)}
    <g fill="#4b5c51" stroke="#6e8170" strokeWidth=".5" opacity=".7">
      <path d="M29 48 52 29 94 31 112 47 88 59 84 82 65 87 49 70 33 67Z M74 92 100 104 113 125 96 157 85 171 76 145 80 123 67 104Z" />
      <path d="M120 35 149 29 166 39 191 34 221 45 266 42 278 63 258 82 230 91 216 117 198 110 183 88 159 77 144 82 126 65Z M137 80 165 85 180 106 165 139 149 148 133 125 122 103Z M221 135 245 126 265 145 254 163 229 164 217 149Z" />
    </g>
    {countries.map(c => { const [x,y]=coords[c.code]??[150,90]; return <g key={c.code} className="map-point" role="button" tabIndex={0} aria-label={`View ${c.name}`} onClick={()=>onSelect(c.code)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(c.code);}}}>
      <title>{c.name}</title><circle cx={x} cy={y} r="10" fill="transparent" />{selected===c.code&&<circle cx={x} cy={y} r="9" fill="none" stroke="#d5eea8" opacity=".5" />}<circle cx={x} cy={y} r={selected===c.code?4:2.8} fill={selected===c.code?'#d5eea8':'#96a58b'} />
    </g>; })}
  </svg>;
}
