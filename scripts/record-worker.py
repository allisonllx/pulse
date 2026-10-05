#!/usr/bin/env python3
"""Start/status/stop the local recorder without installing a system service."""
import os, signal, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
state=root/'.worldview';state.mkdir(exist_ok=True)
pidfile=state/'worker.pid';logfile=state/'worker.log'
def active():
    if not pidfile.exists():return None
    try:
        pid=int(pidfile.read_text())
        command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
        return pid if '-m collector run --panel config/recording-panel.json' in command else None
    except (ValueError,OSError):return None
mode=sys.argv[1] if len(sys.argv)>1 else 'status'
pid=active()
if mode=='start' and not pid:
    with logfile.open('ab') as output:
        process=subprocess.Popen([str(root/'.venv-collector/bin/python'),'-u','-m','collector','run','--panel','config/recording-panel.json','--adapter','http','--windows','60','--publish-output','public/data','--embeddings'],cwd=root,stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True)
    pid=process.pid;pidfile.write_text(str(pid))
    print(f'Recorder started: PID {pid}; log {logfile}. Requires this machine awake and connected. Stops at configured expiry or budget cap.')
elif mode=='stop' and pid:
    os.kill(pid,signal.SIGINT);pidfile.unlink(missing_ok=True);print('Recorder stopping; evidence preserved.')
elif mode not in {'start','stop','status'}:
    raise SystemExit('Usage: record-worker.py start|status|stop')
else:print(f'Recorder PID {pid}; log {logfile}' if pid else 'Recorder is stopped.')
