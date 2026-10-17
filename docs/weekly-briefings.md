# Weekly Pulse

The homepage presents weekly editorial briefings with All and Technology lenses. `/explore` retains the geographic recordings and live scans; legacy `/?scan=...` links forward there. `/briefings?edition=YYYY-MM-DD` opens an archived edition.

## Local operation

```sh
.venv-collector/bin/python -m collector.briefing.cli collect --dry-run
.venv-collector/bin/python -m collector.briefing.cli collect
.venv-collector/bin/python -m collector.briefing.cli build
.venv-collector/bin/python -m collector.briefing.cli publish
npm run build
```

The default edition covers the previous Monday-to-Monday week in Singapore time. `--window-end` accepts a timezone-aware ISO date for a different seven-day window. Collection does not require existing geographic proxy credentials. Private evidence is stored under `.worldview/briefings`, separately from `worldview.sqlite`. `--data-dir`, `--output`, and `--sources` override the defaults. `--fixture-dir` reads source-ID-named `.xml` or `.json` files with zero network traffic.

Publication writes immutable lens files and an archive index, then atomically changes `public/data/briefings/manifest.json`. Failed/empty publications retain the prior manifest. The public manifest for recordings is independent. Rebuild `out/` after publication so static hosting includes new files.

## Verified sources — October 17, 2026

| Source | Method | Live outcome |
| --- | --- | --- |
| BBC News | `https://feeds.bbci.co.uk/news/rss.xml` | 24 dated items |
| BBC Technology | `https://feeds.bbci.co.uk/news/technology/rss.xml` | 21 dated items |
| BBC Business / Culture | Publisher RSS feeds | Verified XML with 49 / 23 feed entries |
| Guardian World / Technology | Publisher RSS feeds | Verified XML with 45 / 31 feed entries |
| NASA | Official news-release RSS | Verified XML with 10 feed entries |
| Hacker News | `https://hnrss.org/frontpage` | 20 posts; discussion links use HN thread URLs, with literal points/comments |
| Kubernetes | GitHub releases REST API, 20-result bound | 20 published releases; edition filtering uses `published_at` |
| YouTube | Pinned yt-dlp + Node, public This week/popularity search | Six dated videos in the integration check |
| Reddit / X | OpenCLI read-only browser adapters | Runtime installed; explicit browser connection still required |
| Search | Disabled capability entry | Search provider not configured |

The GitHub Atom feed was tested but contains update dates without publication dates; the implementation instead uses the [documented releases API](https://docs.github.com/en/rest/releases/releases#list-releases). HN RSS is a third-party feed of public discussions. Counts above are collected records, not necessarily records in the edition window.

Transport allows only configured hosts, with 15-second request timeouts, a 2 MB decoded response limit, 20 attempts per configured source, and at most one transient retry. Rate-limited responses are recorded without immediate retry. Source failures do not stop successful collection. Raw responses remain private.

## Editorial behavior and current limits

The current implementation selects up to 20 developments, reserving 12 places for factual reporting/announcements and 8 for discussion before filling remaining places from eligible records. Factual selection prefers no more than six anchors from one publisher group, relaxing when evidence is scarce. It deduplicates canonical URLs and identical normalized headlines conservatively. Different titles about the same event can remain separate; semantic event clustering is a subsequent improvement.

Scores expose recency, independent publisher corroboration, source-normalized discussion metrics, lens fit, and novelty against the previous archived edition. Unknown metrics give no boost. Novelty contributes zero when no prior-edition baseline exists. Growth requires comparable metric observations at least six hours apart; a single observation is labeled popularity. Counter resets receive no growth boost. Current ranking must not be described as exhaustive platform trends.

Editorial copy currently uses an attributed source excerpt, not generated analysis. `thin` status applies when there are fewer than 15 developments, fewer than 4 themes, or fewer than 2 factual publisher groups. The initial catalog needs more independent reporting and broader categories before a strong general-interest briefing is possible. Query packs are versioned groundwork; live free-text search expansion is not implemented.

The initial October 17 edition covers a rolling seven-day window to demonstrate real data before the first scheduled calendar edition. It has limited observation history and does not imply seven days of engagement measurements.

## Scheduling and delivery

```sh
.venv-collector/bin/python -m collector.briefing.worker status
.venv-collector/bin/python -m collector.briefing.worker tick
.venv-collector/bin/python -m collector.briefing.worker print-launchd
```

The worker uses a process lock and records completed daily actions. An hourly tick collects after 06:00 Singapore time; on Mondays it publishes after 08:00 and rebuilds the static output. Successful actions are not repeated on the same Singapore date. A failed subprocess is not marked successful. Jobs have a ten-minute timeout. `print-launchd` emits a macOS launch agent with the current interpreter and repository paths; it does not install or activate it. Create the private evidence directory before configuring log paths.

Scheduler activation is pending. A sleeping/offline local computer cannot deliver an always-on service. `.openai/hosting.json` identifies `out/` as the deployment artifact; a rebuild updates local assets only. Hosted redeployment remains a separate operation using the configured hosting service. No deployment credentials or deploy command were assumed, and nothing has been deployed or scheduled by this change.

## Verification

```sh
.venv-collector/bin/python -m pytest -q
npm test
npm run typecheck
npm run test:e2e
npm run build
```

Regression tests cover timezone/window boundaries, unsafe URLs, metric validation, immutable observations, gzip handling, request/size limits, redirect checks, RSS/Atom dates, GitHub release dates, balance, clustering, publisher corroboration, atomic publication, locks, and Singapore scheduling. Browser coverage exercises lens switching, source links/gaps, mobile width, missing publications, and the existing explorer routes.

## Remaining plan work

The end-to-end RSS/GitHub/YouTube briefing path and dashboard are implemented. Reddit/X browser adapters are implemented and await user browser setup. Remaining work includes a search provider, broader reporting coverage, semantic event clustering, a labeled 40-signal ranking corpus, scheduler activation, and verified hosted delivery. On-demand sector/topic research remains the next product increment after those operational foundations.

## Social backends and topic labels

Technology membership is independent of evidence type: a Hacker News thread about Claude can be `Technology · AI & models · Community discussion`. The All and Tech grouping now share the same classifier. The catalog recognizes DeepSeek, Claude Code and related AI names, while contextual rules separate neural transformers from electrical equipment or films. Build/publish re-evaluates cached signals against the current catalog without rewriting raw evidence.

YouTube uses `yt-dlp[default]==2026.8.19` from the collector's `social` extra, with Node explicitly enabled. It samples at most three videos from each of two configured queries using the project's existing This week/popularity filter. It downloads metadata only, ignores user yt-dlp configuration/plugins, and never reads browser cookies. Commands have a 75-second timeout and 2 MB output limit; only needed metadata fields are emitted. Entries without an exact publication timestamp are rejected. Publication additionally enforces the edition's seven-day window. These are query samples, not all-platform trends.

```sh
.venv-collector/bin/python -m pip install '.[social]'
```

X and Reddit use the read-only `search` adapters from OpenCLI 2.0.0, following the backend used by Agent-Reach. The runtime is installed privately under `.worldview/tools/opencli` with lifecycle scripts disabled. Reproduce that installation with:

```sh
npm install --prefix .worldview/tools/opencli --ignore-scripts --save-exact @jackwener/opencli@2.0.0
```

To connect your browser:

1. Install the [OpenCLI Browser Bridge extension](https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk) in the Chrome profile you want Pulse to use.
2. Log into X and Reddit in that profile yourself. No passwords or cookies need to be pasted into chat or committed to this repository.
3. Check the connector using `.worldview/tools/opencli/node_modules/.bin/opencli doctor`. With multiple connected profiles, choose one using OpenCLI's profile commands or `OPENCLI_PROFILE`.
4. Explicitly enable browser collection:

```sh
PULSE_BROWSER_SOURCES=1 .venv-collector/bin/python -m collector.briefing.cli collect
```

For scheduled runs, add `PULSE_BROWSER_SOURCES=1` and the chosen `OPENCLI_PROFILE` to the private `.env.local` only after completing that setup. Without the opt-in, Pulse does not invoke OpenCLI or inspect any browser session. The adapters only search: they never post, like, comment, follow, or join communities. Reddit uses top posts within a week; X uses a bounded top-search query with date operators. Exact timestamps are validated again before publication. Chrome/bridge/login availability is still required at collection time.

The browser integration is fixture-tested against the upstream row contracts; it is not claimed live-connected until the user completes the bridge/login step. Agent-Reach itself, Scrapling, and Patchright Enhanced are not required for these paths.
