import { AppearanceEvent, Source, Topic } from './recording';
export type VisualVisitor = AppearanceEvent & { stationary?: boolean; queueIndex?: number };
export function visitorPopulation(topics: Topic[], events: AppearanceEvent[]): VisualVisitor[] {
  const arrivals = new Set(events.filter(e=>e.kind==='arrival').map(e=>`${e.topicId}|${e.itemId}|${e.source}`));
  const residents: VisualVisitor[] = topics.flatMap(t=>t.items.map((item,i)=>({
    id:`${item.observationId}-${item.id}-${i}`,topicId:t.id,itemId:item.id,source:item.source,
    kind:'arrival',window:item.observedAt,stationary:!arrivals.has(`${t.id}|${item.id}|${item.source}`),queueIndex:i
  })));
  return [...residents,...events.filter(e=>e.kind==='departure')];
}
export function visibleEvents(universe: Topic[], events: AppearanceEvent[], ai: boolean, source: Source | 'all', query: string) {
  const ids=new Set(universe.filter(t=>(!ai||t.category==='ai')&&(!query||`${t.label} ${t.aliases.join(' ')}`.toLowerCase().includes(query.toLowerCase()))).map(t=>t.id));
  return events.filter(e=>ids.has(e.topicId)&&(source==='all'||e.source===source));
}
