# Recent updates and demos, October 5 revision

The earlier five-query baseline found generic pages. New YouTube discovery pairs identical English queries and US region settings across country IPs, with the verified “This week” and “Popularity” filter combination. This is the view from each country, not the creator's country or regional audience size. The selected filters are checked in the response; unconfirmed filters yield no accepted items.

Twelve-query catalog: two anchors, then three rotating queries per window. Rotation is deterministic and country-independent. Six pilot countries have five slots; Germany, France and Mexico have two anchors. It replaces their future generic YouTube search jobs, retains the historical controls, and does not add search slots. News, watch phrases and local Gaming continue separately; the Bing baseline was subsequently quarantined, as documented below.

Anchors:
- new AI agent demo
- AI model release benchmark

Rotating YouTube queries:
- AI coding assistant new release demo
- new AI project demo open source
- open source AI agent GitHub release demo
- open source multimodal model release
- AI research paper code implementation
- AI developer tool launch demo
- new music releases official music video
- new album release review
- new indie game release gameplay
- new game update patch gameplay

The site reports upload-age and global view-count strings; preserve them as displayed, alongside their observation timestamps. They are not country-specific views, engagement growth, verified repository stars, X likes/reposts, or evidence of causal propagation. Popularity is YouTube's stated sort mode, not an independent trend detector.

Six Bing expanded-query probes failed relevance review despite successful HTTP/extraction: they returned unrelated pages, including non-X/non-GitHub destinations for site-limited queries. Their raw evidence and failure status remain; rejected results are excluded from normalized topic analysis. `discovery-v1` cannot be enabled for Bing until this is resolved. Indexed X links alone would never establish traction.

Primary references: [YouTube search filters](https://support.google.com/youtube/answer/111997), [Bing advanced search keywords](https://support.microsoft.com/en-us/bing/advanced-search-keywords). The actual filter parameter was taken from the fetched YouTube page's searchFilterRenderer navigation endpoints, not inferred from these help pages.

## Bing baseline quarantine, October 5

Review of Singapore's original baseline found eight Amy Taylor LinkedIn appearances under `gaming` and antibody-drug-conjugate papers under `AI coding tools`. Transport/extraction success was insufficient evidence of query relevance. All Bing normalized items are quarantined pending source-level diagnosis; previously accepted observations are marked `source_relevance_quarantined`, raw files remain, and the pre-quarantine archive preserves the former normalized data. Bing has been removed from the recurring panel. This is a source-quality exclusion, not evidence that these subjects are trending or that attention dropped. The underlying reason for the mismatched responses is unresolved.

## Balanced discovery revision

The active `broad-v2` panel replaces future `discovery-v1` YouTube searches. Each main English window requests three different non-AI categories, followed by the existing two AI anchors. The three-category rotation is identical across country IPs. DE/FR/MX sample the first two broad slots instead of their former AI-only subset; unequal coverage remains visible. Categories rotate every six hours and their two phrase variants alternate across seven-window blocks. Keyword sampling is not a comprehensive platform trending feed.

English catalog:

| Category | Phrase variant 1 | Phrase variant 2 |
|---|---|---|
| sports | soccer match highlights goals | basketball game highlights NBA |
| music | new music release official music video | live concert performance |
| film_tv | new movie official trailer | new TV series review episode |
| gaming | new indie game release gameplay | new game update patch gameplay |
| culture | street food festival vlog | viral dance challenge original |
| science_tech | space mission launch footage | new gadget hands on review |
| public_affairs | breaking news eyewitness report | election debate analysis |

Local broad searches start in SG/JP/BR, with the same three-category schedule, localized phrases, local `gl` and Accept-Language settings. UI language `hl=en` is requested to simplify filter verification, but YouTube can return localized UI labels; English, Japanese and Portuguese selected week/popularity labels were verified from raw responses. Original-language results remain separate from the English control. Phrase profiles for Hindi, French, German and Spanish exist in code but are not yet enabled for recurring broad local search. Existing local News and Gaming collection continue independently.

The English pilot was manually checked across all seven broad categories. It returned match highlights, recent music videos, trailers, indie gameplay, food-festival videos, launch footage and news reports. The initial ambiguous football wording returned both soccer and NFL, and future queries now specify soccer. Search ranking can still include clickbait, promotional videos and irrelevant items; no claim of comprehensive hottest-topic detection or regional audience size is made.

Sports has its own navigation district. Unclassified labels can use the discovery query category as a navigation fallback; that fallback does not prove result relevance or merge topics. Label-derived topic categories take precedence, and multilingual semantic topic memberships are unchanged. Original queries, results and observation windows remain inspectable. Collection retains the existing cap and reserve; dated gaps remain explicit if budget or source access stops samples.
