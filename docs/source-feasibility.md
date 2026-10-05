# Geographic discovery research, round 2 — 2026-10-05

Read-only local evidence inspection and primary-source web research. No credential files read or live proxy probes performed by this researcher.

## Final live follow-up evidence (after 06:26 UTC)

- **YouTube local gaming recovered:** the root collector handled the displayed cookie-consent rejection buttons in English, German and French; successful observations now exist for GB, DE and FR. These earlier gaps were consent handling, not proof those countries could not fetch discovery. Existing English search and gaming coverage extends beyond SG.
- **Bing is working and expanding:** the root decoded Bing tracking wrappers to destination URLs before item identity and removed the accidental `gl` setting. At this read-only snapshot, Bing evidence included eight countries, with collection toward the fifteen-country panel ongoing. This is usable additional public-web coverage. A successful sample in two places remains insufficient for a causal IP claim.
- **Reddit US browser is a confirmed human-verification gate:** observation `90f840c85a69130efc4f5323` saves a DOM titled **Reddit - Prove your humanity**, with visible instructions to complete a challenge and a `www.google.com/recaptcha/api.js` script. There are no feed posts. The initial HTTP page was a JavaScript challenge; rendering reached an explicit CAPTCHA rather than usable content. Stop this automated candidate for the current panel; a larger country grid would multiply the same unresolved gate.
- **Creative Center US remains unclassified blank content:** observation `547c419b748ace55f94123de` has successful before/after geography checks and browser transport accounting, but the saved DOM is only 39 characters with an empty head/body: no title, scripts, trend rows, login message, challenge, or displayed error. The total charge is 6,494 bytes, including 1,104 browser bytes. This does not support calling the target blocked, login-gated, or a parser failure; main-navigation status, final URL and request-failure details were not retained with the raw evidence.
- **Earlier Creative Center SG browser error is different:** observation `f6c3f9316626ea3a98ac19d5` records three `browser_error` attempts, no raw DOM, successful geography checks before each attempt, and a conservative charge of 15,008,466 bytes. The generic `browser_unavailable_or_blocked` label cannot distinguish adapter/navigation failure from a target block. Stop retries under unchanged conditions; only a diagnostic that records those missing facts would justify revisiting it.

The ranked recommendations below were written before those final probes. Their current order is therefore **working Bing and YouTube discovery first**, public Google Trends as the strongest remaining small exploration, then category charts. Reddit and Creative Center should remain visible failed experiments rather than advertised working sources. No additional proxy calls were made for this follow-up.

## The data is not SG-only

The current SQLite evidence has successful English YouTube searches in **SG, US, GB, JP, IN and BR**, ten observations per country across two windows. Gaming discovery succeeds in **SG, US, JP, IN and BR**, twice per country; GB fails twice. News covers fifteen countries. TikTok search/Creative Center were only probed in SG; Instagram keyword search only in US. These last two bounded scopes are not statements about other countries' availability. If the interface suggests all non-News data is SG-only, inspect its active country, source/profile filter, selected window, and coverage messaging against this evidence.

## Failure causes established by saved evidence

| Surface | What actually happened | What it establishes / next action |
|---|---|---|
| TikTok SG search | Original browser allowlist excluded the page's only script host, `sf16-website-login.neutral.ttwstatic.com`. After correcting it and waiting seven seconds, all three new DOMs rendered **Page not available**, with no video links or result arrays. | Original failure had a concrete collector cause. Corrected failure is rendered availability failure. Neither active CAPTCHA nor login requirement is demonstrated. Stop repeating that query; inspect main-document/JSON-response status and browser failures in the next genuinely different probe. |
| TikTok Creative Center SG | Observation records `transport_error`, 32,000 bytes, no raw and no attempt rows. | No target-page evidence exists. This could be connection/location-verification failure; it does not show Creative Center blocked or empty. Establish which stage failed before spending browser bandwidth. |
| Instagram US keyword search | Three HTTP 302 redirects followed by ~418 KB HTTP-200 shell; `og:url` points to `/`, shell includes `PolarisLoggedOutHomePage`, visible content is just Instagram, no posts. | This public keyword route did not deliver search results. Evidence is consistent with logged-out home/auth routing, but final redirect URL and active renderer were not captured. HTTP does not execute its app. Existing Instagram parser only accepts titled `/p/` or `/reel/` anchors, so it also lacks bootstrap/response extraction. Do not call all Instagram publicly inaccessible. |
| YouTube GB Gaming | Both windows save **Before you continue to YouTube** cookie-consent page, no video renderer. | Concrete consent interstitial, not evidence of an anti-bot ban. One browser consent step using **Reject all**, then refetch in the same verified session, is the useful next experiment. |

Do not infer active challenges from occurrences of `captcha`, `login`, or `checkpoint` inside bundles or translation tables. Instagram private-account authorization and browser login are also different from changing IP. Meta's official product is authenticated Professional-account workflows, not anonymous keyword discovery: [Meta-maintained Instagram collection](https://www.postman.com/meta/instagram/folder/u4g5a2a/instagram-api-with-facebook-login).

TikTok officially identifies location, language, device and interactions as recommendation signals; matching content matters strongly for search. This supports a location hypothesis, not guaranteed logged-out endpoint access: [TikTok recommendation explanation](https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content).

## Ranked public-web candidates using existing residential proxies

### 1. Bing organic discovery — strongest practical new IP test

- Exact candidate: `https://www.bing.com/search?q=live+music+tonight&setlang=en`.
- Run same URL/query/English headers in US and SG, without `cc`, `mkt`, saved location or browser geolocation. Pair a broad culture query (`music`) with local-intent discovery (`live music tonight`). Inspect detected location and region as well as organic result IDs/order.
- Extract `li.b_algo > h2 a`, descriptions and canonical destinations; distinguish ads/local cards and decode Bing redirect wrappers when required. Current source parser has a Bing organic branch. A blank `b_algo` extraction needs raw classification before retry.
- Microsoft explicitly says ranking considers country/city/language and location can be inferred from IP. This is a supported hypothesis for proxy value. [Bing ranking and location controls](https://support.microsoft.com/en-us/bing/how-bing-delivers-search-results).
- Secondary query-free surface: `https://www.bing.com/news?setlang=en`; keep topic cards and edition/default region. It requires a distinct card parser.

### 2. Reddit popular — useful culture plus a documented IP signal

- IP-controlled candidate: `https://www.reddit.com/r/popular/best/`, fresh logged-out state, no `geo_filter`.
- Explicit-region controls, verified from current Reddit page links: `https://www.reddit.com/r/popular/best/?geo_filter=sg` and `https://www.reddit.com/r/popular/best/?geo_filter=us`.
- Extract `shreddit-post` attributes `post-title`/`permalink` and community in visible page order, excluding promoted posts. Existing parser supports those title/permalink attributes. If content appears in another layout, add a validated HTML fallback; do not treat a selector miss as blocked.
- Reddit documents IP-based approximate location as the default customization setting, but that account-setting documentation does not prove the logged-out popular page honors it. Compare omitted-region URL across IPs, then crossed explicit-filter/IP controls. [Location policy](https://support.reddithelp.com/hc/en-us/articles/360062429491-Managing-your-Location-Customization-setting), [current public feed](https://www.reddit.com/r/popular/).

### 3. Google Trends Trending Now — better discovery than News RSS, modest proxy necessity

- Default-location candidate: `https://trends.google.com/trending?hl=en-US`.
- Explicit-region control candidate: `https://trends.google.com/trending?geo=SG&hl=en-US` (validate returned location; URL country parameter is not a documented API contract).
- Capture browser-rendered table rows: trend title, bucketed volume, growth, start/status, breakdown, displayed location/sort/timeframe. Google documents public CSV/RSS export; capture the actual export link rather than inventing an undocumented feed endpoint. It covers 100+ countries, updates about every ten minutes and defaults location to user location. [Trending Now Help](https://support.google.com/trends/answer/3076011?hl=en).
- This is public web/export collection, not an API alternative. Explicit regional trends improve Worldview's cultural scope even if changing IP proves unnecessary. Run the default-location surface first to test proxy value.

### 4. YouTube Gaming and charts — build on already usable discovery

- Native public surface: `https://www.youtube.com/gaming` (already successful in five countries).
- Official chart links: `https://charts.youtube.com/charts/TrendingVideos/us/weekly` and `https://charts.youtube.com/charts/TrendingTrailers/US`.
- Gaming parser preserves shelf labels; sampled shelf order is not one global popularity rank. Charts require browser/response extraction on `charts.youtube.com`, preserving actual displayed rank and period. Validate other country segments rather than assuming complete coverage.
- YouTube says trending charts are unpersonalized and country-specific. Explicit country paths demonstrate geography via settings; proxy effects require fixed-path tests. [Official charts Help](https://support.google.com/youtube/answer/7239739?hl=en).

### 5. TikTok Creative Center — diagnose transport, then one alternate surface

- Current public candidate: `https://ads.tiktok.com/creative/creativeCenter/trends?region=SG`.
- Older discovery surface, also currently indexed: `https://ads.tiktok.com/business/creativecenter/hashtag/didyouknow/pc/en`.
- Parse actual ranked hashtag/video rows with declared region/timeframe and displayed metrics, using DOM or the page's own fetched JSON; public first-page availability is unverified through these proxies. Full analytics may require login. [Current Trends Help](https://ads.tiktok.com/resources/help/article/how-to-use-trends?lang=en&redirected=2).
- This is a region-selector source, so do not claim it needs proxies. A fresh `https://www.tiktok.com/foryou?lang=en` is a separate possible IP experiment, but lower priority after the explicit availability failures; limit to one diagnostic with main/JSON-response evidence and no video/media download.

### 6. News HTML and Instagram public profiles — lower priorities

- `https://news.google.com/?hl=en-US` without explicit `gl`/`ceid`: capture displayed region and article links, then repeat fixed US edition across IPs. Do not call personalized For You reproducible while logged out. Google says language/region determine common headline subjects: [News selection Help](https://support.google.com/googlenews/answer/9005749?hl=en).
- A declared public Instagram profile, e.g. `https://www.instagram.com/instagram/`, is a fetchability benchmark with potential app bootstrap/metadata extraction. It is not a geographical discovery feed. Prioritize the keyword probe's redirect diagnosis; collecting fixed creators alone does not demonstrate proxy-dependent worldview differences.

## Admission and promotion

Prefer **Bing + Reddit** next, then Trends if culture coverage matters more than proxy necessity. First collect US/SG once each, single attempt, HTTP bounded at 2 MB; render at most one diagnosed shell per source at 5 MB, no media/images/fonts. Preserve existing 20% reserve, provider expiry and charged-spend admission. Do not multiply an unclassified failure across countries.

Hold URL/query/language/cookies/consent/timeframe constant while IP changes. Repeat successful country samples in independent sticky sessions, alternating order, before causal claims. Report settings-derived geography separately from residual IP differences. Keep concrete consent/auth/transport/page-unavailable/parser-empty statuses visible. Promote collection only after two distinct successful windows and actual extracted rows.

Avoid replacing social failures with Twitch/Spotify/Steam/event-ticket sites: Oxylabs lists entertainment, gaming and ticketing examples among restricted proxy targets. They require provider capability verification first. Instagram/TikTok are not explicitly named in that list; the list is non-exhaustive, so their omission is not a guarantee. [Provider restricted targets](https://developers.oxylabs.io/help-center/most-popular-questions/restricted-targets-proxy-solutions-and-web-scraper-api).


Instagram ordinary browser follow-up (US, October 5): the keyword route renders an explicit login page with “Log into Instagram”, email/username and password inputs, and no posts. This confirms a logged-out authentication gate for this tested route. No account access was attempted. It does not establish every Instagram public page is unavailable.
