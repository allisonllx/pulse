import { describe,expect,it } from 'vitest';
import { readFileSync } from 'node:fs';
import { Recording,Snapshot } from '../../src/lib/recording';
import { knownTopics,rankedTrends,topicJourney } from '../../src/lib/trends';
const data:Recording=JSON.parse(readFileSync('public/data/demo-v1/recording.json','utf8'));
const sample=(country:string,index:number)=>data.snapshots.find(s=>s.country===country&&s.profile==='local'&&s.window===data.windows[index])!;
describe('observed topic analysis',()=>{
 it('does not manufacture growth from a first sample or a gap',()=>{
  const current=sample('SG',2),previous=sample('SG',0);
  expect(rankedTrends(current,undefined).every(t=>t.delta===null)).toBe(true);
  expect(rankedTrends(current,previous).every(t=>t.delta===null)).toBe(true);
 });
 it('uses common successful surfaces for changes and rank weighting',()=>{
  const current=sample('JP',3),previous=sample('JP',2);
  const trends=rankedTrends(current,previous);
  expect(trends.every(t=>t.comparableSurfaces===2)).toBe(true);
  expect(trends.reduce((n,t)=>n+t.share,0)).toBeCloseTo(1);
  expect(rankedTrends(current,previous,'youtube')).toEqual([]);
 });
 it('keeps successful absence at zero and missing evidence as gaps',()=>{
  const journey=topicJourney(data,'local-sg','local','all',sample('SG',3),data.windows[3]);
  expect(journey.rows.find(r=>r.country.code==='JP')!.cells[3].count).toBeNull();
  expect(journey.rows.find(r=>r.country.code==='US')!.cells[3].count).toBe(0);
  expect(journey.rows.find(r=>r.country.code==='SG')!.cells[3].count).toBeGreaterThan(0);
 });
 it('does not show future detections and keeps profiles separate',()=>{
  const d:Recording={...data,snapshots:data.snapshots.filter(s=>!(s.country==='US'&&s.profile==='local'&&s.window===data.windows[0]))};
  const journey=topicJourney(d,'moon','local','all',sample('SG',0),data.windows[0]);
  expect(journey.windows).toHaveLength(1);
  expect(journey.detections.some(r=>r.country.code==='US')).toBe(false);
  expect(journey.rows.find(r=>r.country.code==='US')!.cells[0].count).toBeNull();
 });
 it('keeps watch query series distinct and rejects unrelated query matches',()=>{
  const base=sample('SG',0),item=base.topics[0].items[0];
  const s:Snapshot={...base,coverage:[{...base.coverage[0],surface:'watch_rss',query:'cornell 7',itemCount:2}],topics:[{...base.topics[0],id:'a',items:[{...item,surface:'watch_rss',query:'cornell 7',title:'Cornell case coverage'},{...item,id:'noise',surface:'watch_rss',query:'cornell 7',title:'Unrelated gaming headline'}]}]};
  const d:Recording={...data,snapshots:[s],windows:[s.window]};
  expect(knownTopics(d,'local','all',s.window).some(t=>t.id==='watch:cornell 7')).toBe(true);
  expect(topicJourney(d,'watch:cornell 7','local','all',s,s.window).rows.find(r=>r.country.code==='SG')!.cells[0].count).toBe(1);
 });
 it('finds recorded topics beyond the selected country without inventing matches',()=>{
  expect(knownTopics(data,'local','all',data.windows[0]).some(t=>t.id==='local-jp')).toBe(true);
  expect(knownTopics(data,'local','all',data.windows[0]).some(t=>t.label==='Cornell7')).toBe(false);
 });
});
