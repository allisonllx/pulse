import { describe, expect, it } from 'vitest';
import { buildNeighborhoodLayout, districtFor } from '../../src/lib/neighborhoods';
import type { Topic } from '../../src/lib/recording';

function topic(id: string, category: string, label = id): Topic {
  return { id, category, label, count: 2, score: 1.5, firstSeen: '2026-10-05T00:00:00Z', aliases: [], platforms: { youtube: 1.5 },
    items: ['a', 'b'].map((suffix, index) => ({ id: `${id}-${suffix}`, title: label, url: `https://example.com/${id}/${suffix}`, rank: index + 1,
      source: 'youtube', surface: 'search', query: null, language: 'en', snippet: '', observationId: 'observation', observedAt: '2026-10-05T00:00:00Z' })) };
}
const sample = [topic('a', 'ai', 'AI agents explained'), topic('b', 'ai', 'Building AI agents'), topic('c', 'news', 'Trump announces a policy'),
  topic('d', 'news', 'Trump campaign latest news'), topic('e', 'news', 'Ukraine peace talks'), topic('f', 'gaming', 'Minecraft worlds')];
const serial = (topics: Topic[]) => {
  const result = buildNeighborhoodLayout(topics);
  return { ...result, lots: [...result.lots.entries()] };
};

describe('stable topic neighborhoods', () => {
  it('puts same-category shops in one distinct district and groups shared terms', () => {
    const layout = buildNeighborhoodLayout(sample);
    expect(layout.districts.find(d => d.id === 'ai')?.topicIds).toEqual(['a', 'b']);
    const news = layout.districts.find(d => d.id === 'news')!;
    expect(news.subtopics).toHaveLength(1);
    expect(news.subtopics[0].label).toBe('Trump');
    expect(news.subtopics[0].topicIds).toEqual(['c', 'd']);
    const c = layout.lots.get('c')!, d = layout.lots.get('d')!;
    expect(Math.hypot(c[0] - d[0], c[1] - d[1])).toBeCloseTo(3.2);
    for (const district of layout.districts) for (const id of district.topicIds) {
      const [x, z] = layout.lots.get(id)!;
      expect(Math.abs(x - district.x)).toBeLessThan(district.width / 2 - 1.3);
      expect(Math.abs(z - district.z)).toBeLessThan(district.depth / 2 - 1.3);
    }
  });

  it('is independent of source order and replay counts without mutating evidence', () => {
    const original = structuredClone(sample);
    const base = serial(sample);
    expect(serial([...sample].reverse())).toEqual(base);
    expect(serial(sample.map(t => ({ ...t, count: 0, score: 0, items: [] })))).toEqual(base);
    expect(sample).toEqual(original);
    expect(sample.reduce((n, t) => n + t.count, 0)).toBe(12);
  });

  it('keeps every lot collision-free and inside the city at the 48-shop limit', () => {
    const topics = Array.from({ length: 64 }, (_, i) => topic(`shop-${String(i).padStart(2, '0')}`, ['ai', 'technology', 'gaming', 'music', 'culture', 'news', 'other'][i % 7]));
    const layout = buildNeighborhoodLayout(topics);
    expect(layout.lots.size).toBe(48);
    const positions = [...layout.lots.values()];
    for (let i = 0; i < positions.length; i++) {
      expect(Math.abs(positions[i][0]) + 1.35).toBeLessThan(layout.width / 2);
      expect(Math.abs(positions[i][1]) + 1.35).toBeLessThan(layout.depth / 2);
      for (let j = i + 1; j < positions.length; j++) {
        expect(Math.abs(positions[i][0] - positions[j][0]) >= 2.7 || Math.abs(positions[i][1] - positions[j][1]) >= 2.7).toBe(true);
      }
    }
    for (let i = 0; i < layout.districts.length; i++) for (let j = i + 1; j < layout.districts.length; j++) {
      const a = layout.districts[i], b = layout.districts[j];
      expect(Math.abs(a.x - b.x) >= (a.width + b.width) / 2 || Math.abs(a.z - b.z) >= (a.depth + b.depth) / 2).toBe(true);
    }
  });

  it('uses translated display headlines to organize uncategorized shops conservatively', () => {
    expect(districtFor(topic('election', 'other', 'Presidential election in Brazil'))).toBe('news');
    expect(districtFor(topic('game', 'other', 'New Nintendo games'))).toBe('gaming');
    expect(districtFor(topic('unknown', 'other', 'A neighborhood story'))).toBe('other');
    expect(districtFor(topic('explicit', 'culture', 'AI in films'))).toBe('culture');
    expect(buildNeighborhoodLayout([topic('one', 'news', 'Trump news')]).districts[0].subtopics).toEqual([]);
  });

  it('keeps a three-shop subject group adjacent when it starts at a row edge', () => {
    const topics = [
      ...Array.from({ length: 3 }, (_, i) => topic(`trump-${i}`, 'news', `Trump statement ${i}`)),
      ...Array.from({ length: 3 }, (_, i) => topic(`ukraine-${i}`, 'news', `Ukraine update ${i}`)),
      ...Array.from({ length: 2 }, (_, i) => topic(`nobel-${i}`, 'news', `Nobel announcement ${i}`)),
      ...Array.from({ length: 4 }, (_, i) => topic(`other-${i}`, 'news', `Local report ${i}`)),
    ];
    const layout = buildNeighborhoodLayout(topics);
    const district = layout.districts[0];
    // Twelve shops give four columns. Trump takes the first three lots, so
    // Ukraine starts in the fourth lot and continues onto the next row.
    const group = district.subtopics.find(g => g.label === 'Ukraine')!;
    const positions = group.topicIds.map(id => layout.lots.get(id)!);
    expect(group.topicIds).toHaveLength(3);
    expect(positions[0][1]).not.toBe(positions[1][1]);
    for (let i = 1; i < positions.length; i++) {
      expect(Math.hypot(positions[i][0] - positions[i - 1][0], positions[i][1] - positions[i - 1][1])).toBeCloseTo(3.2);
    }
    expect(Math.max(...positions.map(([x, z]) => Math.hypot(x - group.x, z - group.z)))).toBeLessThan(3.2);
    expect(serial([...topics].reverse())).toEqual(serial(topics));
  });
});
