import { describe, it, expect } from 'vitest';
import { briefingPath, parseBriefing } from '../../src/lib/briefings';

describe('weekly publication boundaries', () => {
  it('only loads JSON inside the briefing publication namespace', () => {
    expect(briefingPath('/data/briefings/2026-10-19/a/all.json')).toBe('/data/briefings/2026-10-19/a/all.json');
    for (const path of ['/data/briefings/../secret.json', 'https://example.com/all.json', '/data/briefings/%2e%2e/a.json']) {
      expect(() => briefingPath(path)).toThrow();
    }
  });
  it('rejects malformed editions before rendering them', () => {
    expect(() => parseBriefing({ schemaVersion: 2 })).toThrow();
    expect(() => parseBriefing({ schemaVersion: 1, lens: 'finance', themes: [] })).toThrow();
  });
});
