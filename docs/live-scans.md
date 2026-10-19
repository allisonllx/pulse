# Geographic keyword scans

Pulse supports keyword → live collection → partial findings → saved snapshot alongside the scheduled recording explorer.

## Run locally

```sh
npm run build
npm run scan:serve
```

Open http://127.0.0.1:8787. During development, run `npm run dev` in another terminal; localhost:3000 connects to the same local worker. `NEXT_PUBLIC_SCAN_API` can override its origin at build time. The Python worker binds to localhost. A static deployment opens saved snapshots; public live collection requires a hosted backend with authentication and request admission.

Existing `.env.local` credentials, `WORLDVIEW_BUDGET_BYTES`, expiry, shared SQLite spending and 20% reserve apply. One scan runs at a time. Requests must be JSON from approved local origins, with a 1–100 character keyword and 1–8 supported countries. A cache hit spends no traffic. Refresh creates a new immutable scan ID.

## Queries and interpretation

Seven logical signals run per viewpoint for a free-text scan: quoted Google web search; `site:instagram.com`, `site:tiktok.com`, `site:x.com`, and `site:reddit.com` queries with the quoted keyword; Google News keyword RSS in the country's edition; and YouTube search with the verified This week + Popularity filters. X queries accept both X and Twitter destination domains. User text stays inside a quoted phrase. The language selector applies one chosen query language to every selected country; enter the phrase in that language. Country-edition News, country-region YouTube, and the verified residential IP remain separately recorded. This is a controlled language setting, not a translation of the user's phrase.

Google holds English language and personalization settings fixed without an explicit country parameter. Residential country is verified before and after every fetch. News also changes edition; YouTube holds US settings fixed. These are country viewpoints, not city-targeted measurements.

Google has one bounded Bing fallback with the same query. Fetches make one attempt. No automatic CAPTCHA solving or repeated browser attempts are included. Platform hostname boundaries and a title/snippet token gate reject unrelated results. Original search-result rank survives filtering, including rank gaps.

Evidence separates discovery engine from destination platform. Keyword relevance is token overlap, not semantic similarity. Freshness and engagement are literal snippet labels, not verified platform metrics. Sort by relevance, search rank, or presence of freshness evidence. Social results are not ranked by inferred platform popularity; YouTube's own verified popularity sort is separate.

Country bars count accepted sampled appearances, not population attention, total posts, local views, trend velocity or diffusion. Missing metrics stay absent. Failed, gated and irrelevant surfaces remain collection steps. [Google documents site-specific queries](https://support.google.com/websearch/answer/2466433?hl=en); [site-query results are not exhaustive](https://developers.google.com/search/docs/monitor-debug/search-operators/all-search-site).

## Storage and publication

Private scan state: `.worldview/scans/<id>.json`. Raw responses stay in the private evidence archive. Scan jobs share the scheduled collector's traffic ledger, but do not affect its promotion health. Regular recording publication excludes scans; scan recordings contain only their own observed jobs.

The frontend polls every 1.5 seconds. New observations update the country comparison, findings and existing city visualization. Completed or partial scans publish to `public/data/scans/<id>.json`; `index.json` holds the latest 24 keyword/location keys. Public documents contain normalized evidence, never credentials, IPs or raw sessions. Rebuild to include new snapshots in the static export. Starter topics say “Live scan” until a real snapshot exists; cached topics show timestamps and offer Refresh live.

## Live verification — October 5, 2026

A bounded Singapore Claude Code scan returned 8 relevant Bing web results, 20 News results and 18 YouTube results. Google HTTP returned JavaScript shells. All four Bing social queries returned off-domain pages and were rejected. One ordinary Google browser render reached an explicit human-verification page. A separate DuckDuckGo HTML diagnostic also reached a human-verification challenge and was not integrated. No challenges were solved.

Live web, News and video collection is verified. Indexed Instagram/TikTok/X/Reddit query generation and filtering are implemented, but usable social results are not verified through these proxy routes. A provider-supported SERP capability or another validated search route is needed before advertising working social discovery.

## Visual comparison

The shared/distinct dot view deduplicates exact result identities across countries. Multicolor dots represent a link observed in multiple viewpoints; separate country groups contain links observed in only one matching sample. If another country lacks a successful matching engine/surface/query observation, the finding goes into a coverage-gap group instead of being called distinct. Selecting a dot reveals presence and best observed rank per country. The existing city comparison uses topic-cluster identities and provides the same interactive view. Counts remain sample-level evidence.


## Cross-market concept explorations

The concept library contains 16 curated bundles across 14 verticals. `config/market-concepts.json` is shared by the UI and collector. Selecting a concept previews its three terms and expansion question; collection begins only on Explore concept. Initial viewpoints are US, Singapore, Japan and South Korea; the country selector remains editable.

Concept scans run web, News and video for each term, plus the four social site queries for the first term: 13 base logical signals per country. Each curated local-language term adds two more jobs in its target country, and up to five Google Search jobs can also fall back to Bing. Admission calculates the exact worst-case reservation before starting. Local additions are labeled local-profile evidence and excluded from the like-for-like English term matrix and exclusive-result grouping. API clients send a supported `conceptId`; arbitrary bundles are not accepted. Cache identity includes the catalog version, terms and countries, and saved scans preserve their own bundle definition. Increment the catalog version when changing a bundle.

Non-English result titles can be translated to English from the scan view. Translation inference runs locally and preserves the source headline; the first use of a language may download its pinned model from Hugging Face. Supported translation languages are German, Spanish, French, Hindi, Indonesian, Japanese, Korean, Portuguese, Swedish and Chinese. Translation controls appear when the local scan service is available; a static-only public deployment does not provide the translation API.

The term matrix uses only exact source/surface/query combinations that succeeded in all selected countries. Each cell counts unique result identities across those common sources, with up to 20 visible dots and the full count. Missing comparable coverage is a gap, never a zero. Clicking a cell filters the findings to that term and country. The overlap diagram still compares exact links; different links about the same business format are not automatically treated as equivalent. Vocabulary, format and variant labels are curated research prompts, not verified claims about regional adoption. Search visibility cannot establish demand, revenue, market maturity or direction of expansion.

Reopening the same concept and viewpoints while collection is active attaches to that scan instead of scheduling duplicate traffic. A different scan waits until the current worker finishes.

`/?scan=<scan-id>` restores a saved exploration and its viewpoints. On the local service it can also resume watching a running scan.

The live boba sample also surfaced Boba Fett results. When those titles are present, the matrix labels the term as including fictional-name matches; its counts remain keyword matches rather than a claim that every result concerns beverages.
