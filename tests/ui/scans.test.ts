import { describe, expect, it } from 'vitest';
import { scanItems, sortScanItems, Scan } from '../../src/lib/scans';
import { Item } from '../../src/lib/recording';

describe('scan evidence ordering',()=>{
  const item=(id:string,rank:number,relevance:number,freshnessLabel:string|null=null):Item&{country:string}=>({id,rank,country:'SG',title:id,url:`https://example.org/${id}`,source:'google_search',surface:'scan_web',query:'foo',language:'en',snippet:'',observationId:'obs',observedAt:'2026-10-05T00:00:00Z',discovery:{platform:'web',engine:'google_search',relevance,freshnessLabel,engagementLabels:[],basis:'public-search'}});
  it('keeps rank, keyword relevance and freshness labeling distinct',()=>{
    const items=[item('a',1,.6),item('b',4,1,'2 days ago'),item('c',2,1)];
    expect(sortScanItems(items,'rank').map(i=>i.id)).toEqual(['a','c','b']);
    expect(sortScanItems(items,'relevance').map(i=>i.id)).toEqual(['c','b','a']);
    expect(sortScanItems(items,'freshness').map(i=>i.id)).toEqual(['b','a','c']);
    expect(items.map(i=>i.id)).toEqual(['a','b','c']);
  });
  it('does not double count a result repeated in topic memberships',()=>{
    const i=item('a',1,1);
    const scan={recording:{snapshots:[{country:'SG',topics:[{items:[i,i]}]}]}} as unknown as Scan;
    expect(scanItems(scan)).toHaveLength(1);
  });
});
