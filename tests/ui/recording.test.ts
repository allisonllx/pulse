import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { compareSnapshots, filterTopics, readRecording, safeUrl, snapshotAt, Snapshot } from '../../src/lib/recording';
const recording = readRecording(JSON.parse(readFileSync('public/data/demo-v1/recording.json','utf8')));
describe('published recording semantics', () => {
  it('marks every illustrative observation as demonstration, with count reconciliation', () => {
    expect(recording.mode).toBe('demo');
    expect(recording.snapshots.length).toBe(96);
    for (const s of recording.snapshots) {
      expect(s.topics.reduce((n,t)=>n+t.count,0)).toBe(s.coverage.filter(c=>c.status==='success').reduce((n,c)=>n+c.itemCount,0));
      for (const t of s.topics) expect(t.count).toBe(t.items.length);
    }
  });
  it('compares only common successful surfaces and excludes missing YouTube', () => {
    const a = snapshotAt(recording,'SG',recording.windows[3],'local')!;
    const b = snapshotAt(recording,'JP',recording.windows[3],'local')!;
    const result = compareSnapshots(a,b)!;
    expect(result.commonSurfaces).toBe(2);
    expect(result.leftCoverage).toBe(3);
    expect(result.rightCoverage).toBe(2);
    expect(result.overlap).not.toBeNull();
    expect(compareSnapshots(a,b,false,'youtube')).toBeNull();
  });
  it('does not compare profiles, dates or empty coverage as zero overlap', () => {
    const a=recording.snapshots[0];
    expect(compareSnapshots(a,{...a,profile:'english'})).toBeNull();
    expect(compareSnapshots(a,{...a,window:recording.windows[1]})).toBeNull();
    expect(compareSnapshots(a,{...a,coverage:[]})).toBeNull();
    expect(compareSnapshots(undefined,a)).toBeNull();
  });
  it('preserves country-specific topic differences on shared coverage', () => {
    const result=compareSnapshots(snapshotAt(recording,'SG',recording.windows[0],'local'),snapshotAt(recording,'JP',recording.windows[0],'local'))!;
    expect(result.leftOnly).toContain('local-sg');
    expect(result.rightOnly).toContain('local-jp');
  });
  it('filters AI and platform with matching counts and safe source links', () => {
    const topics=filterTopics(recording.snapshots[0],true,'youtube');
    expect(topics.length).toBeGreaterThan(0);
    for (const t of topics) { expect(t.category).toBe('ai'); expect(t.count).toBe(t.items.length); expect(t.items.every(i=>i.source==='youtube')).toBe(true); }
    expect(safeUrl('javascript:alert(1)')).toBeNull();
    expect(safeUrl('data:text/html,hello')).toBeNull();
    expect(safeUrl('https://example.com')).toBe('https://example.com/');
  });
  it('does not produce departures for failed observations', () => {
    const failed=snapshotAt(recording,'JP',recording.windows[3],'local')!;
    expect(failed.events.filter(e=>e.source==='youtube')).toEqual([]);
  });
  it('rejects malformed recordings', () => {
    expect(()=>readRecording({})).toThrow();
    expect(()=>readRecording({...recording,windows:['broken']})).toThrow();
    const s = {...recording.snapshots[0],coverage:null} as unknown as Snapshot;
    expect(()=>readRecording({...recording,snapshots:[s]})).toThrow();
  });
});
