# Pulse

**The internet, from everywhere.**

Explore public internet surfaces across countries through cozy 3D cities, geographic keyword scans, and weekly briefings. Topics become storefronts; sampled result appearances become visitors.

## Current status

The geographic recording is complete and available as a dated archive. The current dataset contains **45 recorded windows across October 5–17, 2026**, covering **15 countries** with unequal source coverage and visible collection gaps. The Oxylabs recording subscription expired on October 18; saved recordings and scans work without the collector or proxy subscription.

- **Recording explorer:** country and profile selection, topic neighborhoods, shop spotlight, evidence links, country comparisons, timeline replay, an AI lens, and observed topic trends.
- **Keyword and concept scans:** saved geographic explorations, exact-link overlap, coverage-aware comparisons, local-language query settings, and curated cross-market concept bundles. New collection requires an available local scan service and valid proxy configuration.
- **Translations:** a precomputed English display layer for supported archive languages, plus optional local translation of scan headlines. Original text remains available.
- **Weekly briefings:** published All and Tech editions at `/briefings`. This is a separate evidence layer from the geographic recording; it is not an automatic continuation of the proxy experiment.

Public site: [Pulse](https://worldview-internet-city.allisonlixuan.chatgpt.site/). Its existing URL retains the earlier project name.

## Run locally

Requires Node.js/npm for the frontend and Python 3.12 for the optional collector and scan service.

```sh
npm ci
npm run dev
```

Open [localhost:3000](http://localhost:3000). The home page provides discovery and scan entry points; `/explore` opens the recording and `/briefings` opens weekly editions. Saved data needs no proxy credentials. The separately labeled synthetic demo is available for illustration.

To serve a static build:

```sh
npm run build
npm start
```

For the optional local scan and translation service:

```sh
python3 -m venv .venv-collector
.venv-collector/bin/python -m pip install -e '.[test,browser,embeddings,translations]'
npm run build
npm run scan:serve
```

Open [127.0.0.1:8787](http://127.0.0.1:8787). New scans require valid credentials, an unexpired subscription, and spendable traffic under the configured cap in ignored `.env.local`; starting the service does not renew these. See the [scan runbook](docs/live-scans.md) for query languages, translation models, source behavior, and API configuration.

## What the recording measures

Google News regional RSS feeds supply broad local news. YouTube supplies sampled search and gaming discovery, with coverage varying by country and date. Later search queries rotate sports, music, film/TV, gaming, culture, science/technology, and public affairs alongside AI anchors. Local-language and English-control observations stay separately labeled.

Google Search and direct social discovery were not reliable enough for the recurring panel. Bing's historical baseline was quarantined after irrelevant responses. On-demand scans support indexed social queries, but working TikTok, Instagram, X, and Reddit discovery is not established across countries. See [source feasibility](docs/source-feasibility.md) and [query methodology](docs/search-discovery.md).

One visitor represents one sampled result appearance, not a person or regional audience count. Shop size reflects sampled prominence; arrivals and departures require comparable successful observations. Failed or missed samples create gaps. Topic matching is conservative and can miss multilingual equivalence; exact-link overlap and topic-cluster overlap answer different questions.

Country/time views show first detection **within this recording**. Collection order does not establish where a story originated or how it spread. The city displays a bounded subset of topics; use List view to inspect all topics in a selected snapshot. Mobile, reduced-motion, and WebGL fallback views are supported.

## Data, publishing, and preservation

The frontend reads versioned files under `public/data/`. Its manifest points to an immutable recording; saved scans, translations, and briefings have separate indexes. Collection state, raw responses, credentials, and archive exports remain outside Git and public deployment.

The final evidence export includes SQLite, compressed raw responses, Parquet tables, and checksums. Restoration into an empty directory and equivalent publication were verified. Export files live locally under ignored `artifacts/`; a Git clone contains published normalized data, not the private raw archive.

Publishing local JSON does not update the hosted site. Build and redeploy to the **existing** Sites project in `.openai/hosting.json`. The site works independently of the collection machine.

See the [recording operations runbook](docs/recording-operations.md) for collection, optional watchlists, analysis, publishing, and archive commands.

## Verify

```sh
.venv-collector/bin/python -m pytest -q
npm run typecheck
npm test
npm run test:e2e
npm run build
```

## Documentation

- [Geographic scans and local translations](docs/live-scans.md)
- [Recording operations and preservation](docs/recording-operations.md)
- [Collector internals and budget accounting](collector/README.md)
- [Search queries and revisions](docs/search-discovery.md)
- [Source feasibility and limitations](docs/source-feasibility.md)
- [Public data contract](docs/data-contract.md)
- [Weekly briefing design](docs/superpowers/specs/2026-10-17-weekly-pulse-design.md)
