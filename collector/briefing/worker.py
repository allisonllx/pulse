"""Run from an hourly scheduler; uses Singapore time regardless of host settings."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import plistlib
import subprocess
import sys
from zoneinfo import ZoneInfo
from ..publish import atomic_write, canonical
from .models import timestamp
from .pipeline import ROOT


def due_actions(now, completed):
    local = now.astimezone(ZoneInfo('Asia/Singapore'))
    day = local.date().isoformat()
    actions = []
    if local.hour >= 6 and 'collect:' + day not in completed:
        actions.append('collect')
    if local.weekday() == 0 and local.hour >= 8 and 'publish:' + day not in completed:
        actions.append('publish')
    return actions


@contextmanager
def exclusive_run(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    with (root / 'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Briefing worker already running') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['tick', 'collect', 'publish', 'status', 'print-launchd'])
    parser.add_argument('--data-dir', type=Path, default=ROOT / '.worldview/briefings')
    args = parser.parse_args(argv)
    if args.command == 'print-launchd':
        print(plistlib.dumps(dict(Label='com.pulse.weekly', ProgramArguments=[sys.executable, '-m', 'collector.briefing.worker', 'tick'],
                                  WorkingDirectory=str(ROOT), StartInterval=3600, RunAtLoad=True,
                                  StandardOutPath=str(args.data_dir / 'worker.log'), StandardErrorPath=str(args.data_dir / 'worker-error.log'))).decode())
        return 0
    try:
        with exclusive_run(args.data_dir):
            state_path = args.data_dir / 'worker-state.json'
            state = json.loads(state_path.read_text()) if state_path.exists() else {'completed': [], 'lastResult': None}
            if args.command == 'status':
                print(json.dumps(state)); return 0
            now = datetime.now(timezone.utc)
            actions = due_actions(now, set(state['completed'])) if args.command == 'tick' else [args.command]
            for action in actions:
                process = subprocess.run([sys.executable, '-m', 'collector.briefing.cli', action, '--data-dir', str(args.data_dir)], cwd=ROOT, timeout=600)
                if process.returncode:
                    state['lastResult'] = dict(action=action, status='failed', at=now.isoformat())
                    atomic_write(state_path, canonical(state)); return process.returncode
                if action == 'publish':
                    # The configured hosting serves out/. Rebuild it after local publication.
                    subprocess.run(['npm', 'run', 'build'], cwd=ROOT, timeout=600, check=True)
                key = action + ':' + now.astimezone(ZoneInfo('Asia/Singapore')).date().isoformat()
                state['completed'] = list(dict.fromkeys(state['completed'] + [key]))[-90:]
                state['lastResult'] = dict(action=action, status='success', at=now.isoformat())
                atomic_write(state_path, canonical(state))
            print(json.dumps(state)); return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'failed', 'error': type(exc).__name__})); return 2


if __name__ == '__main__':
    raise SystemExit(main())
