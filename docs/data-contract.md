# Published recording contract (v1)

Public URL `/data/manifest.json` points at immutable `/data/<version>/recording.json`.
Manifest: `{schemaVersion:1,datasetVersion:string,generatedAt:ISO,mode:'demo'|'recording',recordingUrl:string,countries:string[],windows:string[],coverage:{successful:number,failed:number},clusterVersion:string}`.
Recording: `{schemaVersion:1,mode:'demo'|'recording',generatedAt:ISO,clusterVersion:string,countries:Country[],windows:string[],snapshots:Snapshot[]}`.

Country: `{code,name,flag,language}`. Six pilot ISO codes SG, US, GB, JP, IN, BR. Expansion SE, DE, FR, KR, ID, MY, AU, CA, MX.
Snapshot: `{country:string,window:ISO,profile:'local'|'english',coverage:Coverage[],topics:Topic[],events:Event[]}`.
Coverage: `{source:'google_news'|'google_search'|'youtube'|'tiktok',surface:string,query:string|null,status:string,itemCount:number,observedCountry:string|null,observedAt:ISO,observationId:string,bytes:number,promoted:boolean}`.
Topic: `{id:string,label:string,aliases:string[],category:'ai'|'technology'|'culture'|'news'|'gaming'|'music'|'other',score:number,count:number,firstSeen:ISO,platforms:Record<string,number>,items:Item[]}`.
Item: `{id:string,title:string,url:string,rank:number,source:string,surface:string,query:string|null,language:string,snippet:string,observationId:string,observedAt:ISO}`.
Event: `{id:string,topicId:string,itemId:string,source:string,kind:'arrival'|'departure',window:ISO}`.

Events compare only successful snapshots with the same country/profile/source/surface/query. No departure events from failures. One appearance is one item in one successful observation; duplicates within that observation are discarded. URLs must use HTTP(S). Missing comparisons are unavailable, not zero overlap. Scores aggregate reciprocal rank separately for each surface/query; UI comparisons use common successful coverage keys only.

No credentials, raw HTML, cookies, private proxy endpoints or IPs in published JSON. Raw evidence and provenance remain in local exports. Cluster membership versions are persisted.
