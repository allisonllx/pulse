import catalog from '../../config/market-concepts.json';
import { coverageKey, success } from './recording';
import { Scan, scanItems } from './scans';

export type MarketConcept = {id:string;vertical:string;label:string;aliases:{term:string;kind:string}[];marketTerms?:Record<string,string[]|undefined>;question:string;version?:string};
export const MARKET_CONCEPTS:MarketConcept[]=catalog.concepts;
export const CONCEPT_COUNTRIES=catalog.defaultCountries;
export function visibleDotCount(count:number,limit=20) { return {dots:Math.min(Math.max(0,count),limit),overflow:Math.max(0,count-limit)}; }
export function queryTerm(query:string|null) {
  return (query??'').replace(/^site:\S+\s+/, '').replace(/^"|"$/g,'').normalize('NFKC').toLowerCase().trim();
}
/** Compare only the exact source/query surfaces that returned successfully everywhere. */
export function conceptMatrix(scan:Scan,platform='all') {
  const snapshots=scan.recording?.snapshots??[];
  const profileByObservation=new Map(snapshots.flatMap(s=>s.coverage.map(c=>[c.observationId,s.profile] as const)));
  return (scan.concept?.aliases??[]).map(alias=>{
    const matches=(query:string|null)=>queryTerm(query)===queryTerm(alias.term);
    const channel=(surface:string)=>surface.split('_')[1];
    const byCountry=scan.countries.map(country=>new Set(snapshots.filter(s=>s.country===country&&s.profile==='english').flatMap(s=>s.coverage.filter(c=>success(c.status)&&matches(c.query)&&(platform==='all'||channel(c.surface)===platform)).map(coverageKey))));
    const common=new Set([...(byCountry[0]??[])].filter(key=>byCountry.every(keys=>keys.has(key))));
    const ambiguity=alias.term==='boba'&&scanItems(scan).some(i=>matches(i.query)&&/boba fett|star wars/i.test(i.title));
    return {alias,ambiguity,commonSources:common.size,commonKeys:[...common],cells:scan.countries.map((country,index)=>{
      const items=scanItems(scan).filter(i=>i.country===country&&profileByObservation.get(i.observationId)==='english'&&matches(i.query)&&common.has(coverageKey(i)));
      return {country,count:new Set(items.map(i=>i.id)).size,available:common.size>0,successfulSources:byCountry[index].size};
    })};
  });
}
