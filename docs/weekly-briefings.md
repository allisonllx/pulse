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
| Search / Reddit / YouTube / X | Disabled capability entries | No usable provider configured; shown as coverage gaps |

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

The end-to-end RSS/GitHub briefing path and dashboard are implemented. The broader approved plan still requires supported search/Reddit/YouTube/X adapters, a richer multi-publisher catalog, semantic event clustering, a labeled 40-signal ranking corpus, scheduler activation, and verified hosted delivery. On-demand sector/topic research remains the next product increment after those operational foundations.
