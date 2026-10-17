export type Lens = 'all' | 'tech';
export type BriefingLink = { url: string; title: string; source: string; evidenceKind: string; publishedAt: string; discoveryMethod: string };
export type Development = { id: string; headline: string; sector: string; topic: string; whyItMatters: string; editorialBasis: string; publishedAt: string; evidenceLinks: BriefingLink[]; discussionLinks: BriefingLink[]; scoreFactors: Record<string, number>; discussionBasis: string };
export type WeeklyBriefing = { schemaVersion: 1; editionId: string; lens: Lens; windowStart: string; windowEnd: string; generatedAt: string; status: 'complete' | 'degraded' | 'thin'; themes: { id: string; label: string; developments: Development[] }[]; coverage: { scope: string; note: string; sources: { source: string; status: string; itemCount?: number; reason?: string }[] } };
export type Edition = { editionId: string; revision: string; lenses: Record<Lens, string> };

export function briefingPath(value: unknown): string {
  if (typeof value !== 'string' || !/^\/data\/briefings\/[a-zA-Z0-9/_-]+\.json$/.test(value) || value.includes('..')) throw new Error('Invalid briefing path');
  return value;
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid briefing document');
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error('Missing briefing field');
  return value;
}
function date(value: unknown): string {
  const result = text(value);
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(result) || !Number.isFinite(Date.parse(result))) throw new Error('Invalid briefing date');
  return result;
}
function links(value: unknown): BriefingLink[] {
  if (!Array.isArray(value)) throw new Error('Invalid source links');
  return value.map(v => {
    const item = record(v), url = new URL(text(item.url));
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) throw new Error('Invalid evidence URL');
    return { url: url.href, title: text(item.title), source: text(item.source), evidenceKind: text(item.evidenceKind), publishedAt: date(item.publishedAt), discoveryMethod: text(item.discoveryMethod) };
  });
}
export function parseBriefing(value: unknown): WeeklyBriefing {
  const v = record(value), coverage = record(v.coverage);
  if (v.schemaVersion !== 1 || !['all', 'tech'].includes(String(v.lens)) || !['complete', 'degraded', 'thin'].includes(String(v.status)) || !Array.isArray(v.themes) || !Array.isArray(coverage.sources)) throw new Error('Unsupported briefing');
  const windowStart = date(v.windowStart), windowEnd = date(v.windowEnd);
  if (Date.parse(windowStart) >= Date.parse(windowEnd)) throw new Error('Invalid window');
  const themes = v.themes.map(theme => {
    const t = record(theme);
    if (!Array.isArray(t.developments)) throw new Error('Invalid theme');
    return { id: text(t.id), label: text(t.label), developments: t.developments.map(dev => {
      const d = record(dev), publishedAt = date(d.publishedAt);
      if (Date.parse(publishedAt) < Date.parse(windowStart) || Date.parse(publishedAt) >= Date.parse(windowEnd)) throw new Error('Development outside window');
      const scoreFactors = record(d.scoreFactors);
      if (Object.values(scoreFactors).some(x => typeof x !== 'number' || !Number.isFinite(x))) throw new Error('Invalid score');
      return { id: text(d.id), headline: text(d.headline), sector: typeof d.sector === 'string' ? text(d.sector) : v.lens === 'tech' ? 'Technology' : text(t.label),
        topic: typeof d.topic === 'string' ? text(d.topic) : text(t.label), whyItMatters: text(d.whyItMatters), editorialBasis: text(d.editorialBasis), publishedAt,
        evidenceLinks: links(d.evidenceLinks), discussionLinks: links(d.discussionLinks), scoreFactors: scoreFactors as Record<string, number>, discussionBasis: text(d.discussionBasis) };
    }) };
  });
  return { schemaVersion: 1, editionId: text(v.editionId), lens: v.lens as Lens, status: v.status as WeeklyBriefing['status'], windowStart, windowEnd, generatedAt: date(v.generatedAt), themes,
    coverage: { scope: text(coverage.scope), note: text(coverage.note), sources: coverage.sources.map(s => { const x = record(s); return { source: text(x.source), status: text(x.status), itemCount: typeof x.itemCount === 'number' ? x.itemCount : undefined, reason: typeof x.reason === 'string' ? x.reason : undefined }; }) } };
}
async function getJSON(path: string, signal?: AbortSignal) {
  const response = await fetch(briefingPath(path), { cache: 'no-store', signal });
  if (!response.ok) throw new Error(response.status === 404 ? 'No weekly briefing has been published yet.' : 'This edition could not be loaded.');
  return response.json();
}
export async function loadEditions(signal?: AbortSignal): Promise<Edition[]> {
  const manifest = record(await getJSON('/data/briefings/manifest.json', signal));
  if (manifest.schemaVersion !== 1) throw new Error('Unsupported manifest');
  const archive = record(await getJSON(briefingPath(manifest.archiveUrl), signal));
  if (archive.schemaVersion !== 1 || !Array.isArray(archive.editions)) throw new Error('Invalid archive');
  return archive.editions.map(e => { const v = record(e), paths = record(v.lenses); return { editionId: text(v.editionId), revision: text(v.revision), lenses: { all: briefingPath(paths.all), tech: briefingPath(paths.tech) } }; });
}
export async function loadBriefing(edition: Edition, lens: Lens, signal?: AbortSignal) {
  const briefing = parseBriefing(await getJSON(edition.lenses[lens], signal));
  if (briefing.editionId !== edition.editionId || briefing.lens !== lens) throw new Error('Edition mismatch');
  return briefing;
}
