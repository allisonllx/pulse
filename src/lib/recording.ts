export type Source = 'google_news' | 'google_search' | 'youtube' | 'tiktok';
export type Profile = 'local' | 'english';
export type Country = { code: string; name: string; flag: string; language: string };
export type Coverage = { source: Source; surface: string; query: string | null; status: string; itemCount: number; observedCountry: string | null; observedAt: string; observationId: string; bytes: number; promoted: boolean };
export type Item = { id: string; title: string; url: string; rank: number; source: Source; surface: string; query: string | null; language: string; snippet: string; observationId: string; observedAt: string };
export type Topic = { id: string; label: string; aliases: string[]; category: string; score: number; count: number; firstSeen: string; platforms: Partial<Record<Source, number>>; items: Item[] };
export type AppearanceEvent = { id: string; topicId: string; itemId: string; source: Source; kind: 'arrival' | 'departure'; window: string };
export type Snapshot = { country: string; window: string; profile: Profile; coverage: Coverage[]; topics: Topic[]; events: AppearanceEvent[] };
export type Recording = { schemaVersion: 1; mode: 'demo' | 'recording'; generatedAt: string; clusterVersion: string; countries: Country[]; windows: string[]; snapshots: Snapshot[] };
export type Manifest = { schemaVersion: 1; datasetVersion: string; generatedAt: string; mode: 'demo' | 'recording'; recordingUrl: string; countries: string[]; windows: string[]; coverage: { successful: number; failed: number }; clusterVersion: string };
export const PLATFORMS: { id: Source; label: string; color: string; short: string }[] = [
  { id: 'google_news', label: 'Google News', color: '#65d9c0', short: 'NEWS' },
  { id: 'google_search', label: 'Google Search', color: '#f4c078', short: 'SEARCH' },
  { id: 'youtube', label: 'YouTube', color: '#ec8794', short: 'VIDEO' },
  { id: 'tiktok', label: 'TikTok', color: '#a99bea', short: 'SOCIAL' }
];
export const success = (status: string) => status === 'success' || status === 'ok';
export const coverageKey = (c: Pick<Coverage, 'source' | 'surface' | 'query'>) => `${c.source}|${c.surface}|${c.query ?? ''}`;
export function snapshotAt(data: Recording, country: string, window: string, profile: Profile) {
  return data.snapshots.find(s => s.country === country && s.window === window && s.profile === profile);
}
export function filterTopics(snapshot: Snapshot | undefined, ai: boolean, platform: Source | 'all', search = '') {
  return (snapshot?.topics ?? []).map(t => {
    const items = t.items.filter(i => platform === 'all' || i.source === platform);
    return { ...t, items, count: items.length, score: items.reduce((sum, i) => sum + 1 / Math.max(1, i.rank), 0) };
  }).filter(t => t.count > 0 && (!ai || t.category === 'ai') && (!search || `${t.label} ${t.aliases.join(' ')}`.toLowerCase().includes(search.toLowerCase()))).sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
}
export function compareSnapshots(a: Snapshot | undefined, b: Snapshot | undefined, ai = false, platform: Source | 'all' = 'all') {
  if (!a || !b || a.profile !== b.profile || a.window !== b.window) return null;
  const aKeys = new Set(a.coverage.filter(c => success(c.status) && (platform === 'all' || c.source === platform)).map(coverageKey));
  const common = new Set(b.coverage.filter(c => success(c.status) && aKeys.has(coverageKey(c))).map(coverageKey));
  if (!common.size) return null;
  const ids = (s: Snapshot) => new Set(s.topics.filter(t => !ai || t.category === 'ai').filter(t => t.items.some(i => common.has(coverageKey(i)))).map(t => t.id));
  const left = ids(a), right = ids(b);
  const shared = [...left].filter(id => right.has(id));
  const union = new Set([...left, ...right]);
  return { overlap: union.size ? shared.length / union.size : null, shared, leftOnly: [...left].filter(id => !right.has(id)), rightOnly: [...right].filter(id => !left.has(id)), commonSurfaces: common.size, leftCoverage: aKeys.size, rightCoverage: b.coverage.filter(c => success(c.status) && (platform === 'all' || c.source === platform)).length };
}
export function safeUrl(url: string) { try { const parsed = new URL(url); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null; } catch { return null; } }
export function dateLabel(iso: string, full = false) {
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Singapore', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', ...(full ? { year: 'numeric' } : {}) }).format(new Date(iso));
}
export function readRecording(value: unknown): Recording {
  const d = value as Recording;
  if (!d || d.schemaVersion !== 1 || !['demo', 'recording'].includes(d.mode) || !Array.isArray(d.countries) || !Array.isArray(d.windows) || !Array.isArray(d.snapshots)) throw new Error('Unsupported recording format');
  if (d.windows.some(w => !Number.isFinite(Date.parse(w)))) throw new Error('Invalid recording time');
  for (const s of d.snapshots) {
    if (!Array.isArray(s.topics) || !Array.isArray(s.coverage) || !Array.isArray(s.events)) throw new Error('Incomplete snapshot');
    for (const t of s.topics) if (!Array.isArray(t.items) || !Array.isArray(t.aliases) || !Number.isFinite(t.score)) throw new Error('Invalid topic');
  }
  return d;
}
