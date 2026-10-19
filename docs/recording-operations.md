# Recording operations

The October 2026 geographic recording is complete. These commands support offline analysis and preservation, or a future separately authorized collection with valid credentials, budget, and expiry. They do not resume an expired subscription.

## Configuration and collection

Copy `.env.example` to ignored `.env.local` for a new setup. Keep credentials private. The completed experiment used a 5,000,000,000-byte cap with a 20% reserve and a configured stop at the start of October 18, 2026, Singapore time. Do not raise the cap or change expiry simply to bypass an admission failure.

```sh
# Offline admission and job inspection:
.venv-collector/bin/python -m collector collect --once --dry-run
.venv-collector/bin/python -m collector status

# Future collection only with valid configuration:
.venv-collector/bin/python -m collector run --panel config/recording-panel.json --adapter http --windows 44 --publish-output public/data --embeddings
```

`config/recording-panel.json` defines the panel: 15-country local News, six-country English YouTube plus DE/FR/MX expansion, local gaming discovery, and SG/JP/BR local broad queries. This is the planned panel; successful historical coverage varies and must be read from the dataset.

Collection windows are six hours apart at 00:00, 06:00, 12:00, and 18:00 UTC. Missed windows remain gaps; a restart never backfills historical pages with current content. The worker requires the machine to stay awake and connected.

```sh
python3 scripts/record-worker.py status
python3 scripts/record-worker.py start
python3 scripts/record-worker.py stop
```

The worker starts the configured panel with embeddings and optional translation refresh. It stops at its bounded window count, expiry, or budget admission failure. Avoid duplicate collectors. Its private state and log live under `.worldview/`.

## Optional watchlists

No keyword is tracked by default. `config/watch-topics.json` is empty and the detachable worker does not load a watchlist. To explicitly track phrases in a future foreground run, provide a JSON array of phrases using `--watchlist PATH`. The generic `watch_rss` surface and historical watch observations remain supported; series count sampled query results without keyword-specific title filters.

## Analysis and publication

```sh
.venv-collector/bin/python -m collector reextract
.venv-collector/bin/python -m collector summarize --embeddings
.venv-collector/bin/python -m collector publish --embeddings --output public/data
npm run build
npm start
```

The multilingual encoder is `paraphrase-multilingual-MiniLM-L12-v2`. Its model revision and `config/topic-corrections.json` determine cluster versions. Preserve reviewed merges/splits. Without embeddings, the engine reports its conservative token/glossary fallback.

Publication writes immutable recordings and atomically switches the manifest. Large future publications also produce a gzip representation. Rebuild and deploy the static output through the existing Sites project in `.openai/hosting.json`; never create a replacement Site. Browsers poll the manifest, but a local publication alone cannot change a hosted build.

## Evidence export and restoration

```sh
.venv-collector/bin/python -m collector export artifacts/pulse-evidence.zip
.venv-collector/bin/python -m collector --data-dir .worldview-restored restore artifacts/pulse-evidence.zip
```

Restore into an empty directory. Archive validation checks inventory, paths, checksums, database integrity, and raw evidence hashes. To check equivalent publication, publish the restored database with the same corrections and analysis settings and compare the recording and manifest against the source publication.

The completed final export is locally named `artifacts/worldview-evidence-final-2026-10-18.zip`, retaining its original artifact name, with a checksum sidecar. These ignored files are not included in the Git repository or public site. Keep an independent copy for backup.

Internal `.worldview/` paths and `WORLDVIEW_*` environment variables retain their original names for compatibility. They do not change the Pulse product name.
