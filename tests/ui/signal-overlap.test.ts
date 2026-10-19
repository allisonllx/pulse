import { describe, expect, it } from 'vitest';
import { scanSignals } from '../../src/lib/signal-overlap';
import { conceptMatrix, MARKET_CONCEPTS, visibleDotCount } from '../../src/lib/concepts';
import { Scan } from '../../src/lib/scans';
import { Item, Snapshot } from '../../src/lib/recording';

const item=(id:string,rank=1):Item=>({id,title:id,url:`https://example.org/${id}`,rank,source:'google_search',surface:'scan_web_abc',query:'"foo"',language:'en',snippet:'',observationId:'obs',observedAt:'2026-10-05T00:00:00Z'});
const snapshot=(country:string,ids:string[],status='success'):Snapshot=>{const observationId=`${country}-english`;return {country,window:'2026-10-05T00:00:00Z',profile:'english',events:[],coverage:[{source:'google_search',surface:'scan_web_abc',query:'"foo"',status,itemCount:ids.length,observedCountry:country,observedAt:'',observationId,bytes:0,promoted:false}],topics:ids.map(id=>({id,label:id,aliases:[],category:'other',score:1,count:1,firstSeen:'',platforms:{},items:[{...item(id),observationId}]}))};};
function scan(snapshots:Snapshot[]):Scan{return {id:'abc',keyword:'foo',countries:['SG','US'],createdAt:'',status:'complete',planned:14,completed:14,events:[],recording:{schemaVersion:1,mode:'recording',generatedAt:'',clusterVersion:'v1',countries:[],windows:[],snapshots}};}

describe('visual overlap evidence',()=>{
  it('caps drawing work while retaining an explicit overflow count',()=>{
    expect(visibleDotCount(20)).toEqual({dots:20,overflow:0});
    expect(visibleDotCount(28)).toEqual({dots:20,overflow:8});
    expect(visibleDotCount(0)).toEqual({dots:0,overflow:0});
  });
  it('deduplicates shared links and preserves distinct identities',()=>{
    const signals=scanSignals(scan([snapshot('SG',['shared','sg','shared']),snapshot('US',['shared','us'])]));
    expect(signals).toHaveLength(3);
    expect(signals.find(s=>s.id==='shared')?.present).toEqual(['SG','US']);
    expect(signals.find(s=>s.id==='sg')?.unknown).toEqual([]);
    expect(signals.find(s=>s.id==='us')?.present).toEqual(['US']);
  });
  it('marks failed coverage as unknown rather than distinct',()=>{
    const signals=scanSignals(scan([snapshot('SG',['sg']),snapshot('US',[],'failed')]));
    expect(signals[0].unknown).toEqual(['US']);
  });
  it('does not treat a different query or engine as an absent matching result',()=>{
    const us=snapshot('US',[]);us.coverage[0].query='another query';
    expect(scanSignals(scan([snapshot('SG',['sg']),us]))[0].unknown).toEqual(['US']);
  });
  it('does not compare a local-language fetch against an English-profile fetch',()=>{
    const local=snapshot('SG',['sg']);local.profile='local';local.coverage[0].observationId='SG-local';local.topics[0].items[0].observationId='SG-local';
    const english=snapshot('US',[]);
    const signal=scanSignals(scan([local,english]))[0];
    expect(signal.unknown).toEqual(['US']);
  });
});

describe('concept comparison',()=>{
  it('compares matched successful surfaces and deduplicates links',()=>{
    const sg=snapshot('SG',['shared','shared','local']);const us=snapshot('US',['shared']);
    for(const s of [sg,us]){s.coverage[0].query='"bubble tea"';s.topics.forEach(t=>t.items.forEach(i=>i.query='"bubble tea"'));}
    const localized=snapshot('SG',['localized']);localized.profile='local';localized.coverage[0].observationId='SG-local';localized.topics[0].items[0].observationId='SG-local';localized.coverage[0].query='"bubble tea"';localized.topics[0].items[0].query='"bubble tea"';
    const value=scan([sg,us,localized]);value.concept=MARKET_CONCEPTS.find(c=>c.id==='bubble-tea');
    expect(conceptMatrix(value)[0].cells.map(c=>c.count)).toEqual([2,1]);
    expect(conceptMatrix(value)[0].commonSources).toBe(1);
    const ambiguous=snapshot('SG',['Boba Fett']);ambiguous.coverage[0].query='boba';ambiguous.topics[0].items[0].query='boba';
    const boba=scan([ambiguous]);boba.concept=value.concept;
    expect(conceptMatrix(boba)[1].ambiguity).toBe(true);
    expect(conceptMatrix(value)[0].ambiguity).toBe(false);
    us.coverage[0].status='failed';
    expect(conceptMatrix(value)[0].cells.every(c=>!c.available)).toBe(true);
  });
});
