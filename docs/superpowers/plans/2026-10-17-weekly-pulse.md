# Weekly Pulse Implementation Plan

> **For agentic workers:** Execute task-by-task with `executing-plans`. Steps use checkbox syntax. Delegation is optional and requires authorization.

**Goal:** Automatically publish a balanced weekly editorial briefing with All and Tech lenses, source coverage, and archived editions.

**Architecture:** Add a focused `collector/briefing/` package beside the existing geographic collector. Source adapters write normalized observations to a separate SQLite database; deterministic clustering, ranking, and evidence-based copy produce immutable weekly JSON. The static Next.js frontend reads a dedicated manifest and preserves access to the current Worldview explorer.

**Tech Stack:** Python >=3.11, httpx, BeautifulSoup, SQLite, pytest; existing Next.js 16.3.8, React 19, TypeScript, Vitest, Playwright. Reuse installed dependencies first.

**Spec:** `docs/superpowers/specs/2026-10-17-weekly-pulse-design.md`

## Global constraints

- Fully automatic weekly publication; All and Tech are the only v1 lenses.
- Target 15–25 developments and 4–7 themes per lens; publish fewer if evidence is insufficient, with `thin` status. Never fabricate or duplicate items to meet a quota.
- Every selected signal has a validated URL and timezone-aware publication timestamp inside the seven-day window.
- Keep factual evidence, official announcements, and community discussion distinguishable.
- Retain independent source-run outcomes, including disabled and unavailable sources.
- X is optional and feature-gated. Platform access must be verified before advertising it as supported.
- Missing metrics provide no ranking boost. One engagement snapshot is popularity, not velocity.
- Existing geographic collection, budget ledger, promotion health, scans, manifests, and archives continue to use their current contracts.
- No credential files or raw session data enter public JSON.
- Before UI implementation, read the relevant installed Next.js guides under `node_modules/next/dist/docs/`; preserve static export.

## Repository integration and implementation defaults

The current `collector.cli.collect()` requires proxy credentials and writes geography-verified observations. Its `Store.save()` rejects geographic mismatches. Do not insert global briefing data into those tables or call that path for direct RSS/API collection. Reuse pure parsing and atomic-write helpers where their semantics match; do not reuse the geographic admission or health machinery implicitly.

The homepage currently renders `Worldview`. Weekly Pulse becomes the default homepage after its fixture-driven view is ready; retain Worldview at `/explore/`, including forwarding existing `/?scan=...` entry links. `next.config.ts` exports static files, so collection and scheduling run outside Next.js request handlers.

Start with English output and explicitly label coverage as selected English-language sources, not the whole internet. Geographic lenses remain an explorer feature. Broad discovery must include source feeds and category headlines, not only keyword searches. All covers public affairs, science/health, business, culture, and technology; Tech includes AI infrastructure. Curated relevance concepts must not interpret every mention of infrastructure as AI infrastructure.

Default schedule: collect daily at 06:00 Asia/Singapore, publish Monday at 08:00 Asia/Singapore. Publish the preceding Monday 00:00 through current Monday 00:00, using timezone-aware half-open intervals. Scheduler configuration is versioned but installation/activation is a separate operational action. Initial and missed weeks retain an observation-history warning; current results must never be presented as historical measurements.

## File responsibilities

Create `collector/briefing/{models,config,store,transport,normalize,cluster,rank,compose,publish,pipeline,cli}.py`, `collector/briefing/adapters/{base,rss,search,github,reddit,youtube,x}.py`, and package initializers. Each adapter owns only its source conversion; transport owns timeouts and request limits. Keep this package independent of `collector.scans` and the geographic store.

Create `config/briefing-lenses.json` and `config/briefing-sources.json`; `src/lib/briefings.ts`; `src/components/briefing/{WeeklyBriefing,BriefingCard,BriefingCoverage}.tsx`; and `src/app/explore/page.tsx`. Modify `src/app/page.tsx`, `src/app/globals.css`, and collector documentation only at their integration tasks.

Tests: `tests/python/test_briefing_*.py`, `tests/ui/briefings.test.ts`, `tests/browser/briefings.spec.ts`, and `tests/fixtures/briefing/`. Fixtures are hand-authored or sanitized, never copied credentials or private responses.

## Shared interfaces

Python records use camelCase JSON fields from the spec. Implement frozen dataclasses with explicit `to_dict()` conversion and runtime validation. Extend `Signal` with `evidenceKind: factual|announcement|discussion|discovery`, `publisherGroup`, `entities`, and `eventTerms`. Extend metric observations with `observedAt` and `metricKind`; retain `None` for unknown values. Search snippets are `discovery` unless source content or sufficient published metadata validates the claim.

`SourceRun` fields: `id`, `source`, `queryId`, `startedAt`, `finishedAt`, `status` (success|empty|partial|failed|disabled|unavailable), `itemCount`, `rejectedCount`, `errorCode`, `discoveryMethod`, `truncated`.

`FetchRequest` fields: `queryId`, `query`, `lensIds`, `windowStart`, `windowEnd`, `limit`, `cursor`. `FetchResult` contains `signals: list[Signal]`, `run: SourceRun`, `metricSamples: list[MetricSample]`. `Adapter.fetch(request: FetchRequest) -> FetchResult` is the only adapter interface consumed by the pipeline.

Public `WeeklyBriefing`: `schemaVersion: 1`, `editionId`, `revision`, `windowStart`, `windowEnd`, `generatedAt`, `lens`, `status` (complete|degraded|thin), `coverage`, `themes`, `methodVersion`. Each theme has `id`, `label`, `developments`; each development has `id`, `headline`, `whyItMatters`, `editorialBasis`, `publishedAt`, `evidenceLinks`, `discussionLinks`, `scoreFactors`. Links retain source, evidence kind, URL, title, publication time, and discovery method. `whyItMatters` is grounded in supplied evidence; do not present inferred market impact as fact.

## Task 1: Contracts, time windows, and configuration

**Files:** Create models/config modules, configuration JSON, `tests/python/test_briefing_contract.py` and minimal signal fixtures.

**Interfaces:** `load_catalog(path: Path) -> Catalog`; `previous_week(now: datetime, timezone: str = 'Asia/Singapore') -> tuple[datetime, datetime]`; `validate_signal(value: dict) -> Signal`.

- [ ] Write tests rejecting naive dates, future/out-of-window signals, invalid lens IDs, non-http(s) URLs, and numeric metrics containing booleans or nonfinite values. Include publication exactly at the start and end of a window.

```python
def test_previous_week_uses_singapore_boundary():
    start, end = previous_week(datetime.fromisoformat('2026-10-19T00:30:00+08:00'))
    assert start.isoformat() == '2026-10-12T00:00:00+08:00'
    assert end.isoformat() == '2026-10-19T00:00:00+08:00'
```

- [ ] Run `.venv-collector/bin/python -m pytest tests/python/test_briefing_contract.py -q`; confirm missing imports fail before implementation.
- [ ] Implement validation, window calculation, query-pack loading, and config-version hashing. Seed All topic categories and Tech concepts, including AI-infrastructure role/hiring and learning-guide terms with exclusions for unrelated civil infrastructure.
- [ ] Repeat the test command. Commit only task files with message `feat: define weekly briefing contracts`.

## Task 2: Evidence storage and bounded transport

**Files:** Create store/transport/normalize modules and `tests/python/test_briefing_store.py`, `test_briefing_transport.py`.

**Interfaces:** `BriefingStore(root: Path)` owns `briefing.sqlite`; `save_fetch(result: FetchResult) -> None`; `signals_between(start: datetime, end: datetime) -> list[Signal]`; `metric_history(signal_id: str) -> list[MetricSample]`. `Transport.get(url: str, *, params: dict, headers: dict) -> Response` is injected into adapters.

- [ ] Test repeated fetch idempotence, immutable historical metric samples, persisted failed runs, and separate databases. Test URL canonicalization preserving content IDs and stripping tracking parameters only. Test redirect validation before following redirects.
- [ ] Run the two focused files and observe failures.
- [ ] Implement SQLite tables for runs, signal versions, metric samples, and edition revisions. Keep raw response bytes in private content-addressed files. Use 15-second request timeouts, 2 MB response limits, 20 requests per source per collection run, and one retry for transport errors/502/503/504 only. On 429, record rate limiting and defer to a later run. Store safe error codes.
- [ ] Require an explicit allowlist for catalog feed hosts and provider hosts. Reject loopback/private/link-local redirect destinations; block URL userinfo and credential-bearing query parameters from public output. Use direct transport by default; any proxy mode must explicitly join existing spend admission.
- [ ] Repeat focused tests and commit `feat: persist briefing evidence and bounded fetches`.

## Task 3: Factual discovery and a runnable All-lens slice

**Files:** Create adapter base/rss/search modules, pipeline/cli modules, source fixtures, and `test_briefing_sources.py`, `test_briefing_pipeline.py`. Update collector README with a fixture command.

**Interfaces:** `collect(requests: list[FetchRequest], adapters: dict[str, Adapter], store: BriefingStore) -> list[SourceRun]`; CLI `python -m collector.briefing.cli collect --fixture-dir PATH --now ISO` and `collect --dry-run`.

- [ ] Test RSS/Atom dates, empty feeds, malformed entries, inaccessible article content, duplicate syndication, and missing timestamps. Test successful News plus failed search yields persisted evidence and coverage. A dry run must make zero requests.
- [ ] Run `.venv-collector/bin/python -m pytest tests/python/test_briefing_sources.py tests/python/test_briefing_pipeline.py -q` and observe failures.
- [ ] Implement feed collection and an injected search-provider interface. Reuse existing news parsing only through an explicit conversion with fixture tests. Search must report provider and query, not destination platform as fetch origin. Missing search credentials produce `unavailable`; RSS still works.
- [ ] Populate a small versioned catalog with selected broad/category news and official technology feeds. During implementation, verify each URL against its publisher, save a sanitized sample, and record date/method in `docs/weekly-briefings.md`. Do not hard-code an unverified provider endpoint.
- [ ] Run a fixture collection and inspect private store/run summaries. Repeat tests and commit `feat: collect weekly factual signals`.

## Task 4: Tech and community adapters with honest availability

**Files:** Create github/reddit/youtube/x adapters and `test_briefing_community.py`; expand source config and fixtures.

**Interfaces:** Every adapter implements `fetch(FetchRequest) -> FetchResult`; capabilities expose native collection versus indexed discovery and available metrics. X remains disabled by default until validated.

- [ ] Test each adapter against a successful fixture and disabled, forbidden, rate-limited, empty, and missing-date fixtures. Verify indexed Reddit/X discovery cannot produce platform engagement metrics. Verify title keywords alone cannot confer Tech membership without matching configured concepts.
- [ ] Run the community test file and observe failures.
- [ ] Implement GitHub releases and explicitly labeled repository activity; cumulative stars are not weekly growth. Implement YouTube public metadata/search through a verified supported route; transcripts are optional. Implement Reddit through a supported authorized API when available, otherwise clearly labeled indexed discovery. Existing repository evidence records Reddit CAPTCHA and unusable social-search samples, so do not assume those routes work.
- [ ] Implement an X provider boundary with disabled/unavailable states and indexed discovery support where verified. Direct X collection requires a documented working access method; no optional tool installation is necessary for core operation. If evaluating Agent-Reach later, audit its selected backend and pin a version; importing its marketing claims does not validate access.
- [ ] Verify current official API documentation, authentication requirements, quotas, and response shapes during implementation. Record the selected method per source in the source catalog. Optional missing credentials must never block fixture tests or core publication.
- [ ] Repeat focused tests and commit `feat: add tech and discussion source adapters`.

## Task 5: Clustering and explainable scoring

**Files:** Create cluster/rank modules and `test_briefing_ranking.py`; add a labeled corpus of at least 40 signals covering 12 events, reposts, syndicated reporting, ambiguous names, and two weekly windows.

**Interfaces:** `cluster_signals(signals: list[Signal]) -> list[Cluster]`; `rank_clusters(clusters: list[Cluster], lens: str, window_end: datetime, history: list[MetricSample], previous: list[Development]) -> list[RankedCluster]`.

- [ ] Write behavior tests: mirrored wire stories count once for corroboration; two releases by one company stay separate; official announcement plus related discussion cluster together; missing metrics add zero; unavailable sources do not imply lack of conversation; repeat events need a material change to receive novelty credit.
- [ ] Run ranking tests and observe failures.
- [ ] Implement deterministic clustering using canonical identity first, then conservative entity/action/time matching. Require entity and event-term agreement for fuzzy merges; avoid transitive chain merging by comparing every candidate with the cluster representative. Keep ambiguous matches separate. Sort all ties by stable ID.
- [ ] Calculate score factors in [0,1]: recency 25%, independent corroboration 25%, discussion 20%, lens fit 20%, novelty 10%. Recency uses a 72-hour half-life. Discussion uses percentile-normalized `log1p` metrics within source and metric kind; aggregate a source once and cap its contribution. Measured velocity requires at least two comparable samples at least six hours apart; otherwise label the signal popularity. Do not renormalize absent factors to award extra points.
- [ ] Evaluate the labeled corpus, inspecting false merges. Require zero false merges in the regression corpus; adjust thresholds conservatively. Repeat tests and commit `feat: cluster and rank weekly developments`.

## Task 6: Editorial selection, copy, and atomic publication

**Files:** Create compose/publish modules, expand pipeline/cli, and `test_briefing_publication.py`.

**Interfaces:** `compose_briefing(ranked: list[RankedCluster], lens: str, runs: list[SourceRun], window: tuple[datetime, datetime]) -> WeeklyBriefing`; `publish_edition(all_briefing: WeeklyBriefing, tech_briefing: WeeklyBriefing, destination: Path) -> dict`. CLI `build --window-end ISO` reuses saved evidence; `publish --window-end ISO --output PATH` writes only validated output.

- [ ] Test a healthy edition, fewer than 15 eligible events, discussion-only clusters, missing optional sources, no usable evidence, and injected failure before manifest replacement. Assert the prior manifest and archive remain intact on failure.
- [ ] Run publication tests and observe failures.
- [ ] Implement diversity-aware selection: target 20 developments, maximum 25; group into up to 7 configured editorial themes and target at least 4 when supported. Limit one publisher group to 30% of the selected factual anchors, relaxing only with visible thin coverage. Include both factual and discussion content when eligible; do not force unsupported discussion.
- [ ] Generate an evidence-grounded extractive v1: headline and factual synopsis from a selected anchor; `whyItMatters` describes documented scope or observed discussion with citations and `editorialBasis`. No model key is required. Add a future copy-provider interface only when synthesis quality requires it; any generated factual clause must map to supplied evidence and invalid output falls back to extraction.
- [ ] Produce immutable `public/data/briefings/<edition-id>/<revision>/all.json` and `tech.json`, plus an immutable archive index. Atomically replace `public/data/briefings/manifest.json` last; it references both lenses and the matching index. Never rewrite the existing geographic manifest. Empty/unusable evidence fails publication and preserves the last valid edition.
- [ ] Repeat tests, run a fixture build twice, and confirm byte-identical results for identical inputs and fixed times. Commit `feat: publish auditable weekly briefings`.

## Task 7: Static dashboard and archive

**Files:** Create frontend files listed above and browser/UI tests; modify homepage and styles. Add `src/app/briefings/page.tsx` for archive selection using `?edition=...` with manifest-approved IDs.

**Interfaces:** `parseBriefing(value: unknown) -> WeeklyBriefing`; `loadBriefing(manifestUrl: string, lens: Lens, editionId?: string, signal?: AbortSignal) -> Promise<WeeklyBriefing>`. TypeScript fields mirror the public contract.

- [ ] Read installed Next.js static-export, page, and client-component guides before coding. Inspect current Worldview deep-link behavior so existing scan URLs still open their exploration.
- [ ] Add Vitest cases for malformed manifests, unsupported schemas, path traversal, incomplete links, and missing metric values. Add Playwright fixture interception for All/Tech switching, archive navigation, discussion labels, degraded coverage, empty state, loading/error states, keyboard interaction, and mobile width.
- [ ] Run `npm test -- tests/ui/briefings.test.ts`; confirm failures before implementation.
- [ ] Implement a compact briefing header, All/Tech controls, 4–7 theme sections where available, concise cards, source links, coverage details, and archive access. Display unavailable engagement as absent, never zero. Use ordinary escaped text and validated external URLs. On stale data, retain the edition date visibly.
- [ ] Make `/` render WeeklyBriefing; link to `/explore/` for Worldview. Detect legacy `scan` query parameters in a client component and forward them to `/explore/` preserving the scan ID. Keep archive navigation within static routes.
- [ ] Run `npm run typecheck`, focused UI/browser tests, and `npm run build`. Confirm both homepage and explorer export successfully. Commit `feat: present weekly pulse and tech briefings`.

## Task 8: Scheduled operation and delivery to the static site

**Files:** Create `scripts/briefing-worker.py`, `ops/weekly-pulse/` scheduler templates, `docs/weekly-briefings.md`, and `test_briefing_schedule.py`.

**Interfaces:** `run_collection(now: datetime) -> RunReport`; `run_publication(window_end: datetime) -> PublicationReport`. Worker subcommands `collect`, `publish`, and `status`; timestamps and paths are explicit arguments.

- [ ] Test overlapping invocations, already-published edition, failed collection, late data, missed publication, timeout, and restart. Verify reranking needs no network and late data creates a new revision rather than changing old artifacts.
- [ ] Run schedule tests and observe failures.
- [ ] Implement a process lock, run IDs, bounded duration, machine-readable status, and nonzero exit on failed publication. Keep collection daily and publication weekly. No long-running foreground sleep loop.
- [ ] Supply macOS launchd templates for the current local collector with absolute paths filled by an installation command. Default to 06:00 daily collection and Monday 08:00 publication in Asia/Singapore, with timezone conversion inside the worker. The templates remain inactive until operational deployment is requested.
- [ ] Document an external scheduler/container alternative for an always-on host. Static hosting cannot execute Python jobs. Inspect the project's actual hosting configuration during implementation and choose one durable delivery path: upload validated briefing assets through the existing hosting pipeline, or trigger its verified build/deploy mechanism after local publication. Local JSON creation alone does not count as live automated publishing.
- [ ] Document required environment variable names, selected providers, cost/request caps, rollback to an earlier immutable manifest, and how source gaps appear. Do not install schedules, buy API access, or deploy as part of this planning task.
- [ ] Repeat focused tests and commit `feat: schedule weekly briefing operations`.

## Task 9: Release verification and acceptance

**Files:** Add release fixtures and verification notes to `docs/weekly-briefings.md`; update README entry points.

- [ ] Run the complete fixture flow: daily collections on two timestamps, weekly build, atomic publish, static build, browser lens/archive checks. Include an unavailable X source and a rate-limited Reddit source.
- [ ] Run `.venv-collector/bin/python -m pytest`, `npm test`, `npm run typecheck`, `npm run test:e2e`, and `npm run build`. Investigate failures against the pre-change baseline; preserve unrelated work.
- [ ] Perform one bounded live smoke test only with configured sources and explicit provider budgets; record actual request count and returned date/metric quality. A native source graduates from unavailable to supported only when this test returns valid items. No repeated unchanged challenge probes.
- [ ] Review 20 selected clusters by hand for false merges, title/claim support, publisher independence, source balance, and link health. Record observed limitations and tune only with regression cases.
- [ ] Confirm older archives, geographic recordings, scan deep links, and the source-health panel remain usable. Confirm no private raw evidence is inside `out/`.
- [ ] Commit only release documentation and task-owned verification artifacts. Report whether local execution, scheduler activation, and hosting delivery have each been verified separately.

## Subsequent increment: on-demand topic and sector research

After weekly publication is stable, write a separate implementation plan for a hosted research request using the shared FetchRequest, adapters, clustering, and ranking interfaces. Queries such as “AI infrastructure roles” and “AI infrastructure guide” should use explicit intent labels (hiring versus learning) and source/query expansion. Reuse the current scan service's admission concepts only after authentication, request budgets, and deployment are specified. This increment does not block Weekly Pulse v1.

## Plan review

Coverage: Tasks 1–3 implement contracts, All discovery, and evidence storage; Task 4 adds Tech/community/X capabilities; Task 5 handles clustering/ranking; Task 6 handles editorial copy and immutable publication; Task 7 implements the dashboard/archive; Task 8 handles scheduling and static-host delivery; Task 9 verifies acceptance. Topic research remains a separately planned increment, as approved.

Implementation clarifications: editorial counts are targets conditioned on evidence; repeated daily observations are required for measured velocity; copy is extractive until a separately configured synthesis provider is justified. These make thin coverage and missing provider credentials operable without inventing data.
