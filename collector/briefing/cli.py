"""Collect selected feeds and publish a weekly edition for static hosting."""
import argparse
from datetime import datetime, timezone, timedelta
from dataclasses import replace
import json
from pathlib import Path
from dotenv import load_dotenv
from .cluster import cluster_signals
from .config import load_catalog, matching_lenses
from .compose import compose_briefing
from .models import previous_week, timestamp
from .pipeline import collect_sources, ROOT
from .publish import publish_edition
from .rank import rank_clusters
from .store import BriefingStore


def main(argv=None):
    load_dotenv(ROOT / '.env.local', override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['collect', 'build', 'publish', 'status'])
    parser.add_argument('--data-dir', type=Path, default=ROOT / '.worldview/briefings')
    parser.add_argument('--output', type=Path, default=ROOT / 'public/data/briefings')
    parser.add_argument('--sources', type=Path, default=ROOT / 'config/briefing-sources.json')
    parser.add_argument('--fixture-dir', type=Path)
    parser.add_argument('--now', default=datetime.now(timezone.utc).isoformat())
    parser.add_argument('--window-end', help='Explicit end of the seven-day edition window, with timezone')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        now = timestamp(args.now)
        with BriefingStore(args.data_dir) as store:
            if args.command == 'collect':
                sources = json.loads(args.sources.read_text())['sources']
                result = collect_sources(sources, store, now.isoformat(), fixture_dir=args.fixture_dir, dry_run=args.dry_run)
                if not args.dry_run and not any(run['status'] in {'success', 'partial'} for run in result):
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 2
            elif args.command == 'status':
                result = store.runs()
            else:
                start, end = previous_week(now)
                if args.window_end:
                    end = timestamp(args.window_end); start = end - timedelta(days=7)
                if end > now:
                    raise ValueError('Edition window cannot end in the future')
                signals = store.signals_between(start, end)
                catalog = load_catalog(ROOT / 'config/briefing-lenses.json')
                # Re-evaluate navigation against the current catalog; evidence stays immutable.
                signals = [replace(s, lensCandidates=['all', 'tech'] if s.sourceType == 'github'
                                   else matching_lenses(s.title + ' ' + (s.excerpt or ''), catalog)) for s in signals]
                if not signals:
                    raise ValueError('No dated evidence in this window; last publication preserved')
                clusters = cluster_signals(signals)
                history = [sample for signal in signals for sample in store.metric_history(signal.id)]
                previous = None
                manifest_path = args.output / 'manifest.json'
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text())
                    archive = json.loads((args.output / manifest['archiveUrl'].removeprefix('/data/briefings/')).read_text())
                    older = [entry for entry in archive['editions'] if entry['editionId'] < end.strftime('%Y-%m-%d')]
                    if older:
                        previous = {}
                        for lens in ('all', 'tech'):
                            path = older[0]['lenses'][lens].removeprefix('/data/briefings/')
                            previous[lens] = [item for theme in json.loads((args.output / path).read_text())['themes'] for item in theme['developments']]
                latest_runs = {}
                for run in store.runs():
                    if start <= timestamp(run['startedAt']) <= now:
                        latest_runs[run['source']] = run
                briefings = {lens: compose_briefing(rank_clusters(clusters, lens, end.isoformat(), history=history,
                                                               previous=previous[lens] if previous else None), lens,
                                                   list(latest_runs.values()), (start.isoformat(), end.isoformat()))
                             for lens in ('all', 'tech')}
                result = briefings if args.command == 'build' else publish_edition(briefings['all'], briefings['tech'], args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except (ValueError, OSError, KeyError) as exc:
        # Do not expose transport URLs or provider credentials in errors.
        print(json.dumps({'status': 'failed', 'error': type(exc).__name__}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
