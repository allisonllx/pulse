# Worldview collector

This Python package collects evidence locally and publishes the exact v1 interface in `docs/data-contract.md`. Its publisher emits only recording mode: an empty database produces an empty recording, never invented observations. The frontend synthetic demo is maintained separately.

## Install and offline checks

```sh
python3 -m venv .venv-collector
.venv-collector/bin/python -m pip install -e '.[test]'
.venv-collector/bin/python -m pytest -q
.venv-collector/bin/python -m collector init
.venv-collector/bin/python -m collector collect --once --dry-run
.venv-collector/bin/python -m collector run --dry-run --windows 44
```

The commands above do not consume proxy traffic. Copy `.env.example` to `.env.local` and supply an Oxylabs residential username/password and explicit `WORLDVIEW_BUDGET_BYTES` only when authorized to harvest. Existing environment values win; `.env.local` wins over `.env`. Credentials are not printed or written to SQLite, raw manifests, exports, or public JSON. Local evidence and exports can contain third-party page content; keep them outside the public site.

## Collection and scheduling

```sh
.venv-collector/bin/python -m collector collect --once --countries SG --sources google_news --profile local
.venv-collector/bin/python -m collector collect --once --countries SG,US,GB,JP,IN,BR --sources google_search,youtube --profile english
.venv-collector/bin/python -m collector collect --once --news-surface local_html
.venv-collector/bin/python -m collector run --windows 44
.venv-collector/bin/python -m collector status
```

`collect` performs one six-hour UTC window. `run` remains in the foreground, waits for the next window, and stops after a bounded number of windows (default 44, maximum 60). No background service, polling installation, or credentials discovery is performed. Stop with Ctrl-C. To target the provider's precise expiry date, choose the start time/windows explicitly and run `collect --once` for the final window before expiry; `WORLDVIEW_EXPIRES_AT` stops requests at the configured expiry.

Six pilot countries produce 66 observations/window: six broad Google News local feeds plus five English queries on Google Search and YouTube in each country. `--expand` adds SE, DE, FR, KR, ID, MY, AU, CA, MX. The five frozen queries are AI agents, AI coding tools, latest AI models, music, and gaming. English experiments use `hl=en`, US platform country settings, no login, and no personalized search, while the residential proxy country changes. Broad local News uses each country's local language and edition. RSS and HTML have explicitly different surfaces and are never compared as the same experiment.

Google News/Search/YouTube use HTTP with a bounded browser fallback by default. Use `--adapter http` for the validated ongoing panel. Browser overrides are available with `--adapter playwright`. Install only when needed:

```sh
.venv-collector/bin/python -m pip install -e '.[browser]'
.venv-collector/bin/python -m playwright install chromium
.venv-collector/bin/python -m collector collect --once --countries SG --sources google_news --news-surface local_html --adapter playwright
.venv-collector/bin/python -m collector collect --once --countries SG --sources tiktok
```

TikTok is an experimental capability and is capped to one query/country job per invocation. There is no scrolling or sustained feed traversal. Browser jobs restrict hostnames, block images/media/fonts, admit at most 40 requests, stop loading at a five MB transfer ceiling, and use a fresh context. The HTTP response ceiling is two MB; location responses are capped at 32 KB. All jobs use up to three attempts with bounded backoff. Consent, CAPTCHA, unavailable browser, malformed feeds, and empty extraction are visible failures, not successful empty lists.

Every attempt verifies `https://ip.oxylabs.io/location` before and after the target fetch through the identical country/sticky-session credentials. The actual Oxylabs multi-provider response is checked for country consensus; disagreement or wrong country fails. Only an opaque session hash, country result, extraction version, effective settings, timestamp, byte estimate, and raw HTML/RSS hash are persisted. Raw evidence is gzip compressed and content addressed. A source/country pair promotes after two consecutive verified successful six-hour windows; a failure resets its streak. Promotion reflects historical state at each observation, not a promise that future requests will work.

## Traffic budget

`status` and dry-run reports show budget, bytes spent, 20% reserve, remaining spendable bytes, job count and worst-case projection. For `run --dry-run`, `projectedRunBytes` covers the selected windows. A batch is rejected before network traffic if its remaining jobs do not fit. Each job reserves its worst-case allocation transactionally in SQLite, preventing concurrent collectors from admitting the same funds. Interruptions retain a conservative full-job traffic charge. Restarted jobs recover after a five-minute lease and must fit the remaining budget again.

Accounting includes request/header overhead, raw transferred response bytes, both location checks, browser network events, and failed attempts. HTTP and browser transport errors with unknown in-flight bytes are conservatively charged their full cap. Provider billing can include protocol overhead and browser cancellation in-flight buffers that cannot be measured exactly from the client; compare local estimates with provider usage before increasing the explicit cap. No quota API or automated spending is claimed.

## Topic analysis and publication

```sh
.venv-collector/bin/python -m collector summarize
.venv-collector/bin/python -m collector publish --output public/data
```

The default engine is explicitly labeled `deterministic-token-fallback`: exact URLs are shared across languages/sources, a small translation glossary supports common multilingual concepts, and entity/number compatibility prevents common similar-name collisions. It is conservative and is not a semantic multilingual embedding model. For optional embeddings:

```sh
.venv-collector/bin/python -m pip install -e '.[embeddings]'
.venv-collector/bin/python -m collector summarize --embeddings
.venv-collector/bin/python -m collector publish --embeddings --output public/data
```

This explicitly loads `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (and may download model assets). If unavailable, the method is visibly labeled as fallback. Memberships, stable topic IDs and every cluster-version membership are persisted. `config/topic-corrections.json` accepts a version, `merges` mapping old topic IDs to target IDs, and `splits` mapping item IDs to chosen topic IDs; cycles fail. Change the version whenever reviewing corrections, then summarize/publish again. Model-based similarity uses a 0.82 cosine cutoff with entity/number guards; this threshold still requires human review on real harvested languages.

Published files are immutable and content addressed. A temporary file is fsynced before atomic replacement of `manifest.json`. Repeated publishing of unchanged observations/corrections yields the same version. Public JSON contains only the v1 fields, no raw evidence or private proxy metadata. Topics count each item once per successful observation, retain source/surface/query links, and sum reciprocal ranks for those appearances. Events require the same country/profile/source/surface/query in consecutive successful six-hour windows. Failures and missing windows break comparison continuity; they do not produce departures or a zero-overlap claim. The first observation has no invented arrival events.

## Portable evidence

```sh
.venv-collector/bin/python -m collector export artifacts/worldview-evidence.zip
.venv-collector/bin/python -m collector --data-dir .worldview-restored restore artifacts/worldview-evidence.zip
```

Exports contain a consistent SQLite backup, raw gzip evidence, Parquet tables (pyarrow), and SHA-256 checksums. Restore checks the complete inventory, duplicate paths, traversal, symlinks, size limits, checksums, SQLite integrity/schema, and raw evidence hashes before atomically installing a clean SQLite backup into an empty directory. It never overwrites existing recordings. Checksums protect against accidental corruption; they do not authenticate a malicious publisher.

## Verification and remaining live work

Fixture tests cover the extractors, duplicate URLs, proxy geography mismatch/changes, provider consensus, retries and failed-byte charging, secret redaction, leases/restarts/concurrent budget admission, promotion/reset, incomplete observations, contiguous events, missing-window gaps, deterministic publication, corrections, Parquet export/restore, corruption and path traversal. The labeled 50-case match-review corpus is a small regression fixture, not an evaluation on harvested headlines.

The October 5 pilot verified Google News in all 15 countries and YouTube in the original six. Google Search and the bounded TikTok probe failed extraction and are excluded from the ongoing panel. The multilingual model was installed and smoke-tested with Portuguese and Japanese matches. Eleven days of history still require elapsed collection time. Source HTML changes and platform blocking remain operational risks.

Run the validated mixed panel, publishing local snapshots after each window:

```sh
.venv-collector/bin/python -m collector run --panel config/recording-panel.json --adapter http --windows 44 --publish-output public/data --embeddings
```

This worker requires the local machine to remain awake and connected. Static public deployments must be updated with newly published local files; a local publish does not silently redeploy the public site.

Oxylabs syntax/response references: [residential quick start](https://oxylabs.io/blog/residential-proxies-quick-start-guide), [official location response example](https://github.com/oxylabs/wget-proxy), [session control](https://developers.oxylabs.io/products/proxies/residential-proxies/session-control).
