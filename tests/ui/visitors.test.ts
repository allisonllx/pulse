import { describe,it,expect } from 'vitest';
import { visitorPopulation,visibleEvents } from '../../src/lib/visitors';
import { AppearanceEvent,Topic } from '../../src/lib/recording';
const topic:Topic={id:'agents',label:'AI agents',category:'ai',score:1,count:1,firstSeen:'2026-10-05T00:00:00Z',aliases:[],platforms:{youtube:1},items:[{id:'video',title:'Agents explained',url:'https://example.com',rank:1,source:'youtube',surface:'search',query:'AI agents',language:'en',snippet:'',observationId:'o1',observedAt:'2026-10-05T00:00:00Z'}]};
const departure:AppearanceEvent={id:'e1',topicId:'agents',itemId:'video',source:'youtube',kind:'departure',window:'2026-10-05T06:00:00Z'};
describe('result customers and vanished storefronts',()=>{
  it('shows one resident per current appearance even without change events',()=>{
    const people=visitorPopulation([topic],[]);
    expect(people).toHaveLength(1);expect(people[0].stationary).toBe(true);
  });
  it('animates each arrival once without doubling the current population',()=>{
    const arrival={...departure,kind:'arrival' as const};
    const people=visitorPopulation([topic],[arrival]);
    expect(people).toHaveLength(1);expect(people[0].stationary).toBe(false);
  });
  it('keeps departures when the topic has vanished from the current frame',()=>{
    expect(visibleEvents([topic],[departure],true,'all','')).toEqual([departure]);
    expect(visitorPopulation([],visibleEvents([topic],[departure],true,'all',''))).toEqual([departure]);
    expect(visibleEvents([topic],[departure],false,'google_news','')).toEqual([]);
  });
});
