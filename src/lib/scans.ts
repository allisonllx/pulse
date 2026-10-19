import { Item, Recording } from './recording';
import type { MarketConcept } from './concepts';

export type Discovery = { platform: string; engine: string; relevance: number; freshnessLabel: string | null; engagementLabels: string[]; basis: string };
export type ScanEvent = { country: string; source: string; channel: string; query: string; status: string; itemCount: number; observedAt: string; fallback: boolean; profile?:string; language?:string; error?:string|null };
export type Scan = { concept?:MarketConcept; id: string; keyword: string; countries: string[]; queryLanguage?:string; createdAt: string; status: 'queued'|'running'|'complete'|'partial'|'failed'; planned: number; completed: number; events: ScanEvent[]; recording: Recording | null; active?: {country: string; source: string; query: string; channel: string}; error?: string };
export type ScanSummary = Pick<Scan, 'id'|'keyword'|'countries'|'createdAt'|'status'|'queryLanguage'> & {conceptId?:string};
export const SCAN_COUNTRIES = [ ['SG','Singapore'],['US','United States'],['GB','United Kingdom'],['JP','Japan'],['KR','South Korea'],['SE','Sweden'],['IN','India'],['BR','Brazil'] ];
export const STARTER_TOPICS = ['Claude Code','Labubu','DeepSeek','BYD','F1','K-pop'];
export function scanApi() {
  if (process.env.NEXT_PUBLIC_SCAN_API) return process.env.NEXT_PUBLIC_SCAN_API.replace(/\/$/, '');
  return typeof window !== 'undefined' && ['localhost','127.0.0.1'].includes(window.location.hostname) && window.location.port !== '8787' ? 'http://127.0.0.1:8787' : '';
}
export function hasLocalScanService() {
  return Boolean(process.env.NEXT_PUBLIC_SCAN_API) || (typeof window !== 'undefined' && ['localhost','127.0.0.1'].includes(window.location.hostname));
}
export function scanItems(scan: Scan): (Item & { country: string; discovery?: Discovery })[] {
  const seen = new Set<string>();
  return (scan.recording?.snapshots ?? []).flatMap(s => s.topics.flatMap(t => t.items.map(i => ({...i, country: s.country})))).filter(i => {
    const key = `${i.country}|${i.observationId}|${i.id}`;
    if (seen.has(key)) return false; seen.add(key); return true;
  });
}
export function sortScanItems(items: ReturnType<typeof scanItems>, order: 'relevance'|'rank'|'freshness') {
  return [...items].sort((a,b) => {
    if (order === 'relevance') return (b.discovery?.relevance ?? 0) - (a.discovery?.relevance ?? 0) || a.rank - b.rank;
    // Freshness labels can be relative or absolute. We group labeled results without inventing comparable dates.
    if (order === 'freshness') return Number(Boolean(b.discovery?.freshnessLabel)) - Number(Boolean(a.discovery?.freshnessLabel)) || a.rank - b.rank;
    return a.rank - b.rank;
  });
}
