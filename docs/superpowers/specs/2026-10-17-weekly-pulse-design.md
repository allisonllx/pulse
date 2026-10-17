# Weekly Pulse Design

## Purpose

Build the first Pulse product increment as a fully automated weekly editorial briefing. It answers, for a fixed seven-day window: what changed, what people are discussing, and why it matters. The briefing must be balanced between reported developments and public discussion signals, while keeping the two kinds of evidence distinct.

The first release publishes two lenses:

- **All** — broad developments and discussion across the project’s supported domains.
- **Tech** — a technology-focused subset, including AI infrastructure when relevant.

On-demand sector and topic research follows in a later increment. It must reuse the collection, normalization, clustering, and ranking system specified here rather than introduce a separate pipeline.

## Scope and non-goals

### In scope

- A scheduled, fully automatic weekly scan and publish run.
- A concise editorial dashboard: 15–25 ranked developments per lens, grouped into 4–7 named themes.
- News/RSS/search as primary factual evidence and public discussion sources as enrichment.
- Independent adapters for Reddit, YouTube, GitHub, and best-effort public X collection.
- Explicit coverage and source-health metadata.
- Archived snapshots that support future week-over-week comparisons.

### Out of scope

- Login-required collection, CAPTCHA solving, anti-bot circumvention, or stealth/WAF-bypass tooling.
- Treating platform engagement as proof of a factual claim.
- Every industry or arbitrary user-defined sector in v1.
- A generic chat interface or a second, bespoke pipeline for search.
- Human review or manual publishing as a required step.

## Product behavior

The default dashboard shows the most recently published weekly briefing. A viewer can switch between **All** and **Tech** without re-running collection. Each lens contains:

1. Scan-window and coverage summary: exact time window, attempted/succeeded sources, and known gaps.
2. A short list of named themes.
3. Ranked development clusters within each theme.
4. For every development: headline, concise `whyItMatters`, publication time, primary evidence links, and separately labeled discussion links.
5. Links to prior weekly snapshots.

The UI must state a degraded source clearly. A completed briefing with an unavailable adapter is valid; the dashboard must not represent it as exhaustive coverage.

## Architecture

### Data flow

```text
All/Tech query packs
        |
        v
source adapters -> normalized raw signals -> deduplicate and cluster
        |                                         |
        v                                         v
source run status                          score and select themes
                                                  |
                                                  v
                                    published weekly briefing + archive
                                                  |
                                                  v
                                              dashboard
```

### Query packs and lenses

The All and Tech lenses are versioned configuration, not hard-coded component logic. Each pack supplies source-specific queries plus inclusion/exclusion concepts. The Tech pack begins broad; AI infrastructure is represented through concept and query expansion, including jobs/roles, model serving, GPU and cloud infrastructure, platform tooling, and practical guides. The future research feature uses the same pack format with a user-supplied query.

### Source adapters

Every adapter implements a source-local fetch strategy and returns normalized signals. Initial adapters are:

| Adapter | Purpose | Role in ranking |
| --- | --- | --- |
| News/RSS/search | Reported events and primary or reputable secondary evidence | factual backbone |
| Reddit | Public community reaction, questions, and recurring concerns | discussion enrichment |
| YouTube | Public tutorial, launch, and discussion metadata/transcript signals where accessible | discussion enrichment |
| GitHub | Releases, repository activity, and developer adoption signals | Tech evidence and enrichment |
| X | Publicly accessible posts and search results only; availability is not guaranteed | optional discussion enrichment |

Adapters fail independently. A failure produces a structured source-run error and coverage entry; it never prevents publication from successful adapters. X must be feature-gated and must not be required for a successful Tech or All scan.

### Canonical signal contract

Adapters emit a source-agnostic `Signal` record. The exact source-specific payload may be retained separately for diagnostics, but ranking and publishing depend only on the canonical shape.

```ts
type SourceType = "news" | "rss" | "search" | "reddit" | "youtube" | "github" | "x";

type Signal = {
  id: string;
  canonicalUrl: string;
  source: string;
  sourceType: SourceType;
  publishedAt: string;
  collectedAt: string;
  title: string;
  excerpt: string | null;
  authorOrPublisher: string | null;
  lensCandidates: ("all" | "tech")[];
  matchedQueries: string[];
  metrics: Record<string, number | null>;
  evidenceUrls: string[];
};
```

Signals with missing publication timestamps may be stored for diagnostics but cannot enter the weekly ranked briefing. Canonical URLs are normalized before deduplication.

### Clustering, scoring, and selection

Deduplication removes alternate URLs or repeat fetches of the same item. Clustering groups evidence and discussion about the same development under one theme/development cluster. A cluster may contain official material, reporting, and community discussion, but its links must remain typed.

Cluster scores are explainable and include:

- **Recency:** decay within the fixed seven-day window.
- **Corroboration:** independent factual sources strengthen a development.
- **Discussion velocity:** source-normalized engagement or repeated discussion; unavailable metrics add no boost.
- **Lens fit:** match strength against the active pack’s concepts and queries.
- **Novelty:** avoid repeats unless a material update has occurred.

No single raw engagement metric may dominate the score. A discussion-only cluster can appear only when labeled as a developing community signal and cannot be phrased as confirmed news.

The selector chooses 15–25 clusters for a lens and organizes them into 4–7 themes. It favors diversity: near-duplicate clusters and one-source dominance are suppressed after ranking. Each published cluster includes stored score factors so the UI can later explain its selection.

## Storage and publishing

Raw signals, source-run records, and published briefing snapshots are separate artifacts:

- **Raw signals:** immutable inputs for a scan; allow re-ranking without another network fetch.
- **Source runs:** adapter, query, start/end time, status, count, and safe error summary.
- **Briefing:** the validated, UI-ready editorial JSON for one `weekStart` and one lens.

Publishing is atomic: a manifest only points to a briefing after every validation succeeds. A failed run never overwrites the most recent valid briefing. Archived snapshots remain addressable by week.

## Reliability and safety

- Apply source-level timeouts, bounded result limits, and a single configured retry policy only for transient transport errors.
- Respect publicly available access paths, source terms, and rate limits; do not automate credentials or bypass site controls.
- Keep source links and timestamps for auditability.
- Record missing/degraded coverage in the output.
- Sanitize excerpts and source content before rendering.

## Testing and acceptance criteria

### Tests

- Adapter tests use recorded fixtures and verify conversion to `Signal` records, canonical URL handling, timestamp rules, and failure results.
- Query-pack tests verify the All and Tech membership rules, including AI-infrastructure concept expansion.
- Clustering tests cover duplicate reports, one development across factual and discussion sources, and unrelated similarly named items.
- Ranking tests verify recency, corroboration, normalized discussion velocity, novelty, and that missing metrics cannot inflate a result.
- Publishing tests verify atomic manifests, historical snapshot retention, and a valid degraded-source briefing.
- UI tests verify lens switching, typed evidence/discussion links, and coverage-gap display.

### Acceptance criteria

1. A scheduled run publishes one valid All and Tech briefing for a seven-day window without manual intervention.
2. Every displayed item has a canonical source URL, publication timestamp, and a distinct evidence/discussion classification.
3. A failed or disabled adapter leaves a valid briefing available and visibly records the gap.
4. Briefings contain 15–25 clusters and 4–7 themes per lens after a normally successful scan.
5. The Tech lens surfaces AI-infrastructure material when it matches its configured concepts, without a dedicated UI filter in v1.
6. A past weekly briefing remains accessible after a subsequent run publishes.

## Delivery sequence

1. Establish canonical contracts, storage boundaries, fixture-driven tests, and the All-lens factual backbone.
2. Add the Tech query pack, GitHub/Reddit/YouTube adapters, clustering, and transparent ranking.
3. Publish weekly briefing artifacts; build the All/Tech dashboard, coverage panel, and archive navigation.
4. Add the feature-gated, best-effort public X adapter.
5. Add on-demand topic/sector research using the same pipeline.
