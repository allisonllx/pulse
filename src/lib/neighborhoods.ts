import type { Topic } from './recording';

export type DistrictId = 'ai' | 'technology' | 'gaming' | 'music' | 'culture' | 'news' | 'other';
export type Neighborhood = { id: DistrictId; label: string; color: string; x: number; z: number; width: number; depth: number; topicIds: string[]; subtopics: { label: string; x: number; z: number; topicIds: string[] }[] };
export type NeighborhoodLayout = { lots: Map<string, [number, number]>; districts: Neighborhood[]; topicIds: string[]; width: number; depth: number };
const DISTRICTS: { id: DistrictId; label: string; color: string }[] = [
  { id: 'ai', label: 'AI & agents', color: '#c3d5bc' },
  { id: 'technology', label: 'Technology', color: '#b9d4dc' },
  { id: 'gaming', label: 'Gaming', color: '#d4c4e2' },
  { id: 'music', label: 'Music', color: '#e7bfc6' },
  { id: 'culture', label: 'Culture & sport', color: '#e8d4af' },
  { id: 'news', label: 'World news', color: '#c5d0d6' },
  { id: 'other', label: 'Around town', color: '#d2d5ba' },
];
const SPACING = 3.2;
const GAP = 1.6;

/** Display neighborhoods are navigational groups, never new topic memberships. */
export function districtFor(topic: Pick<Topic, 'category' | 'label'>): DistrictId {
  if (topic.category !== 'other' && DISTRICTS.some(d => d.id === topic.category)) return topic.category as DistrictId;
  const label = topic.label.toLowerCase();
  if (/\b(ai|artificial intelligence|chatgpt|openai|anthropic|claude|llm|agentic)\b/.test(label)) return 'ai';
  if (/\b(gaming|games?|playstation|xbox|nintendo|minecraft|roblox)\b/.test(label)) return 'gaming';
  if (/\b(music|songs?|singer|concert|album|spotify)\b/.test(label)) return 'music';
  if (/\b(technology|software|coding|iphone|android|developer|chip|computing)\b/.test(label)) return 'technology';
  if (/\b(film|movie|actor|football|soccer|cricket|tennis|sport|bachelor|nobel|literature)\b/.test(label)) return 'culture';
  if (/\b(election|president|parliament|minister|trump|bolsonaro|lula|ukraine|war|attack|police|storm|charged|government|court|vote|gaza|israel|rape|assault|arrest|accused|criminal|murder|fires?|jail|haze|lawsuit|scandal|cornell|pm wong)\b/.test(label)) return 'news';
  return 'other';
}

const SHARED_TERMS: [string, RegExp][] = [
  ['AI agents', /\b(ai agents?|agentic|agent framework)\b/i],
  ['Coding tools', /\b(coding|code assistant|pair programming|developer tools)\b/i],
  ['AI models', /\b(ai models?|llm|language models?)\b/i],
  ['OpenAI', /\b(openai|chatgpt)\b/i],
  ['Bolsonaro', /\bbolsonaro\b/i], ['Lula', /\blula\b/i],
  ['Trump', /\btrump\b/i], ['Ukraine', /\bukrain(e|ian)\b/i],
  ['Gaza', /\bgaza\b/i], ['Elections', /\b(elections?|voting|ballot|runoff)\b/i],
  ['Cornell', /\bcornell\b/i],
  ['Nobel prizes', /\bnobel\b/i], ['Football', /\b(football|soccer)\b/i],
  ['Nintendo', /\bnintendo\b/i], ['PlayStation', /\bplaystation\b/i],
];

function relatedGroups(topics: Topic[]) {
  const remaining = new Set(topics.map(t => t.id));
  const candidates = SHARED_TERMS.map(([label, pattern], index) => ({ label, index, topics: topics.filter(t => pattern.test(t.label)) }))
    .filter(group => group.topics.length >= 2).sort((a, b) => b.topics.length - a.topics.length || a.index - b.index);
  const groups: { label: string | null; topics: Topic[] }[] = [];
  for (const candidate of candidates) {
    const members = candidate.topics.filter(t => remaining.has(t.id));
    if (members.length < 2) continue;
    members.forEach(t => remaining.delete(t.id));
    groups.push({ label: candidate.label, topics: members });
  }
  if (remaining.size) groups.push({ label: null, topics: topics.filter(t => remaining.has(t.id)) });
  return groups;
}

/** The fixed allTopics universe, rather than visible frame counts, determines lots. */
export function buildNeighborhoodLayout(allTopics: Topic[], limit = 48): NeighborhoodLayout {
  const unique = new Map<string, Topic>();
  for (const topic of [...allTopics].sort((a, b) => a.id.localeCompare(b.id) || a.label.localeCompare(b.label))) {
    if (!unique.has(topic.id)) unique.set(topic.id, topic);
  }
  const topics = [...unique.values()].slice(0, Math.max(0, Math.min(48, limit)));
  const plans = DISTRICTS.map(d => {
    const members = topics.filter(t => districtFor(t) === d.id);
    const groups = relatedGroups(members);
    const columns = Math.min(6, Math.max(1, Math.ceil(Math.sqrt(members.length))));
    return { ...d, groups, members, columns, width: columns * SPACING + 1, depth: Math.ceil(members.length / columns) * SPACING + 1.5 };
  }).filter(d => d.members.length).sort((a, b) => b.members.length - a.members.length || a.id.localeCompare(b.id));
  const targetWidth = Math.max(14, ...plans.map(d => d.width), Math.ceil(Math.sqrt(plans.reduce((area, d) => area + (d.width + GAP) * (d.depth + GAP), 0) * 1.25) / 2) * 2);
  const districts: Neighborhood[] = [], lots = new Map<string, [number, number]>();
  const packed: { left: number; top: number; width: number; depth: number }[] = [];
  let width = 0, packedDepth = 0;
  for (const plan of plans) {
    const candidates = [0, ...packed.map(d => d.left + d.width + GAP)].filter(left => left + plan.width <= targetWidth);
    const options = candidates.map(left => {
      const top = Math.max(0, ...packed.filter(d => left < d.left + d.width + GAP && left + plan.width + GAP > d.left).map(d => d.top + d.depth + GAP));
      const nextWidth = Math.max(width, left + plan.width), nextDepth = Math.max(packedDepth, top + plan.depth);
      return { left, top, area: nextWidth * nextDepth + Math.abs(nextWidth - nextDepth) * 8 };
    }).sort((a, b) => a.area - b.area || a.top - b.top || a.left - b.left);
    const { left, top } = options[0];
    const x = left + plan.width / 2, z = top + plan.depth / 2;
    const ordered = plan.groups.flatMap(group => group.topics);
    // Consecutive shared-subject members follow one continuous path, including
    // at row boundaries; a row-major wrap would separate them across the block.
    ordered.forEach((topic, index) => {
      const row = Math.floor(index / plan.columns);
      const column = row % 2 === 0 ? index % plan.columns : plan.columns - 1 - index % plan.columns;
      lots.set(topic.id, [left + .5 + SPACING / 2 + column * SPACING,
        top + .7 + SPACING / 2 + row * SPACING]);
    });
    const subtopics = plan.groups.filter(group => group.label !== null).map(group => {
      const positions = group.topics.map(topic => lots.get(topic.id)!);
      return { label: group.label!, x: positions.reduce((sum, p) => sum + p[0], 0) / positions.length,
        z: positions.reduce((sum, p) => sum + p[1], 0) / positions.length, topicIds: group.topics.map(t => t.id) };
    });
    districts.push({ id: plan.id, label: plan.label, color: plan.color, x, z, width: plan.width, depth: plan.depth,
      topicIds: ordered.map(t => t.id), subtopics });
    packed.push({ left, top, width: plan.width, depth: plan.depth });
    width = Math.max(width, left + plan.width); packedDepth = Math.max(packedDepth, top + plan.depth);
  }
  const depth = Math.max(8, packedDepth);
  width = Math.max(10, width);
  for (const position of lots.values()) { position[0] -= width / 2; position[1] -= depth / 2; }
  for (const district of districts) {
    district.x -= width / 2; district.z -= depth / 2;
    district.subtopics.forEach(group => { group.x -= width / 2; group.z -= depth / 2; });
  }
  return { lots, districts, topicIds: topics.map(t => t.id), width: width + 2, depth: depth + 2 };
}
