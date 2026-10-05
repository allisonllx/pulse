# Worldview

A recording of public internet surfaces from different countries, explored as cozy 3D cities. Topics are storefronts; result appearances are little customers. The public app runs independently of the local collector.

## Open the city

```sh
npm ci
npm run dev
```

Open http://localhost:3000. Choose a country and observation profile, inspect a shop, compare another country, or scrub the timeline. Click a shop or topic to focus it: other shops dim and a warm spotlight appears. Clear shop focus restores the full city. The Trends button opens rank-weighted cluster prominence, comparable-sample change, country/time matrices, and observed detection cohorts. Shared and distinctive comparison topics are clickable. The **AI lens** filters technology/model topics. Mobile and WebGL-unavailable browsers get a list view. Reduced motion shows customers without animation.

The checked-in demonstration is visibly synthetic. `public/data/demo-manifest.json` always opens that separate recording; `public/data/manifest.json` points to the published dataset. Live collection never fabricates missing observations. A newly published real recording replaces the default demonstration, with a button to explore the demo separately.

## Collect real observations

```sh
python3 -m venv .venv-collector
.venv-collector/bin/python -m pip install -e '.[test,browser,embeddings]'
.venv-collector/bin/python -m playwright install chromium
cp .env.example .env.local
```

Fill in your residential proxy credentials, project traffic cap, and exact expiry in `.env.local`. Keep this file private. The current project cap is **5,000,000,000 bytes** with **1,000,000,000 reserved**. The configured stop date is conservatively the start of **October 18, 2026, Singapore time**; change it to your provider's exact expiry if needed.

```sh
# No traffic: inspect admission limits and jobs.
.venv-collector/bin/python -m collector collect --once --dry-run
# A bounded first-country pilot.
.venv-collector/bin/python -m collector collect --once --countries SG --sources google_news,youtube --adapter http
# Validated panel: 15 local News countries, six English YouTube countries.
.venv-collector/bin/python -m collector run --panel config/recording-panel.json --adapter http --windows 44 --publish-output public/data --embeddings
# An optional browser feasibility probe, not a full unsupported harvest.
.venv-collector/bin/python -m collector collect --once --countries SG --sources google_search --queries 'AI agents' --adapter playwright --retry-failed
.venv-collector/bin/python -m collector status
```

For the detachable local worker (stops automatically at the configured expiry or budget cap):

```sh
python3 scripts/record-worker.py start
python3 scripts/record-worker.py status
python3 scripts/record-worker.py stop
```

Collection windows start at 00:00, 06:00, 12:00, and 18:00 UTC (08:00, 14:00, 20:00, 02:00 SGT). The worker stops after its bounded windows, on expiry, or when budget admission fails. Restarting never backfills an old time window with a new page. Missed jobs remain visible gaps.

English translations for French, Spanish, Portuguese and German are precomputed with pinned local models. The language toggle preserves originals alongside translated evidence; other languages retain their original text. Translation failures preserve the recording and never stop harvesting. The watcher polls translation updates separately.

The validated worker also collects local YouTube Gaming discovery where available and tracks the exact phrase **cornell 7** using `config/watch-topics.json` in the six-country panel. Gaming ranks mean sampled order within public shelves, not a global popularity ranking. Cornell series exclude query noise without Cornell named in the title. Queries are a separate signal from semantic topic clusters.

Local news uses a **regional Google News RSS surface**, explicitly identified as `local_rss`; it does not claim to reproduce a personalized homepage. `--news-surface local_html` enables the public page experiment. The historical English search baseline uses five fixed queries: AI agents, AI coding tools, latest AI models, music, gaming. Google/YouTube region settings remain US, with English language, while the proxy country changes. India defaults to Hindi, Malaysia to Malay for local profiles; these are selected views, not a claim to represent every local language.

Source reliability is determined by real probes. The initial TikTok browser filter blocked ttwstatic.com scripts; a corrected probe rendered Page not available. Instagram public keyword search yielded no extractable posts. A Creative Center probe failed transport and is inconclusive. These experiments do not establish that those platforms are impossible to collect. Residential credentials do not imply access to Oxylabs Web Scraper API or Browser products. A fixed-US-edition News feed probe across SG/US overlapped18 of20results; this is exploratory, not evidence of an IP effect. Google Search/TikTok can remain blocked; failures are preserved. The automatic adapter tries HTTP before bounded browser fallback for compatible failures. `--adapter http` is suitable for the validated, cheaper core. Promotion requires consecutive successful collection windows; a single pilot is not enough.

## Analyze, publish, and preserve

```sh
.venv-collector/bin/python -m collector reextract
.venv-collector/bin/python -m collector summarize --embeddings
.venv-collector/bin/python -m collector publish --embeddings --output public/data
npm run build
npm start
.venv-collector/bin/python -m collector export artifacts/worldview-evidence.zip
.venv-collector/bin/python -m collector --data-dir .worldview-restored restore artifacts/worldview-evidence.zip
```

`publish` creates immutable JSON and atomically switches the manifest. **Deploy the new static build after publishing** to update a hosted site; writing local JSON alone does not update the public URL. Browsers check their published manifest every minute and follow the newest frame when already viewing the latest; historical selections remain fixed. The local worker never exposes your computer/database to the public.

Next.js produces portable static output in `out/`, compatible with Vercel or Sites. The current Sites project is defined in `.openai/hosting.json`; ask Codex to republish that same site after updating observations. Vercel alternative: authenticate the Vercel CLI, then `npx vercel deploy --prod`. No credentials or raw evidence belong in either deployment.

The multilingual encoder is `paraphrase-multilingual-MiniLM-L12-v2`; its model revision and correction configuration influence the cluster version. Use `config/topic-corrections.json` for reviewed merges/splits. Without `--embeddings`, the engine uses a conservative token/glossary fallback, explicitly reported by the CLI. Neither the 50-case regression corpus nor the initial recording is a population-wide attention study.

## Meaning and limits

- One appearance is one result within a successful source/surface/query observation. Current results are customers; actual change events animate arrivals and departures. Failed windows never invent departures.
- Country overlap compares only shared successful surfaces in the same profile and time window. Missing evidence is unavailable, not zero attention.
- Animation interpolates sample events; it does not measure real users, model-provider requests, or precise real-world arrival times.
- The archive preserves raw evidence, SQLite, Parquet, and checksums. Restore validates inventory, paths, hashes, and database integrity before installing into an empty directory.
- Proxy-dependent history stays dated after expiry. Future API data must use a separately labeled layer.

## Verify

```sh
.venv-collector/bin/python -m pytest -q
npm run typecheck
npm test
npm run test:e2e
npm run build
```

See [collector guide](collector/README.md), [public contract](docs/data-contract.md), and [implementation ledger](docs/implementation.md). The eleven-day archive and expiry-day final harvest require the local worker to run over time; implementing the software does not manufacture that history.


City shops now sit in colored, labeled topic neighborhoods. Smaller shared-subject clouds organize related shops without merging topic memberships. The fixed country/profile topic universe determines replay positions. Source coverage across countries and the current view's source context expose English controls rather than implying News is the entire recording.

The recurring panel adds Bing's public HTML searches in all fifteen countries (identical English settings, no explicit market parameter), YouTube English discovery in Germany, France and Mexico, and local Gaming discovery in Mexico, Germany and France. Germany/France/UK Gaming uses a normal browser rejecting consent in the displayed language. `queries` narrows expansion panels; explicit panel `adapter` overrides the global adapter. Historical control observations remain intact; future YouTube queries use the revision below. These additions start when actually collected; earlier windows retain gaps. See [source feasibility](docs/source-feasibility.md) for diagnosed TikTok, Instagram and Reddit failures, remaining candidates and the limits of proxy/IP inference.


### Recent-update search revision
YouTube English discovery uses `querySet: discovery-v1`: a 12-query catalog, two recurring tech anchors and three globally coordinated rotating queries per six-hour window. Expansion DE/FR/MX retains two anchor slots. It replaces future generic YouTube controls while retaining their original historical samples. Requests use the site's verified This week + Popularity filter (`sp=CAMSAggD`), with `surface=discovery_week_popular`; this describes upload freshness and platform ranking, not origin country or causal spread. Missing rotating-query samples are gaps, not disappearances. Upload-age and displayed platform-wide view strings are preserved in result snippets and shown in evidence. These view labels are separate from sampled prominence and are not converted into regional audience counts or growth rates.

The expanded Bing pilot was rejected after manual relevance review: site-limited queries returned unrelated domains and broader phrases returned unrelated dictionary/login/homepage results. Its raw evidence is retained with failed/reviewed relevance status; these samples do not supply city topics. Legacy Bing queries remain clearly labeled control observations until a reliable alternative is verified. X posts and repository traction are therefore not advertised as collected signals. Full catalog and query/metadata rules: [collector/discovery.py](collector/discovery.py).
