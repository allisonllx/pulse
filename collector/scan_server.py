"""Local scan worker and static site host. Run: python -m collector.scan_server."""
from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .scans import DEFAULT_COUNTRIES, ScanManager, normalize_countries, normalize_keyword
from .settings import Settings
from .concepts import get_concept, CONCEPT_COUNTRIES


def make_handler(manager, executor, gate, directory='out', port=8787):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def allowed(self):
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            origins = {f'http://{h}' for h in hosts} | {'http://127.0.0.1:3000', 'http://localhost:3000'}
            return self.headers.get('Host') in hosts and (not self.headers.get('Origin') or self.headers['Origin'] in origins)

        def end_headers(self):
            origin = self.headers.get('Origin')
            if origin and self.allowed():
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')
            super().end_headers()

        def respond(self, status, value):
            raw = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            if not self.allowed():return self.respond(403, {'error': 'Origin is not permitted.'})
            self.send_response(204)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_GET(self):
            path = urlsplit(self.path).path
            if path.startswith('/api/') or path.startswith('/data/scans/'):
                if not self.allowed():return self.respond(403, {'error': 'Origin is not permitted.'})
                if path in {'/api/scans', '/data/scans/index.json'}:
                    return self.respond(200, manager.catalog())
                prefix = '/api/scans/' if path.startswith('/api/scans/') else '/data/scans/'
                try:
                    scan_id = path.removeprefix(prefix).removesuffix('.json')
                    scan = manager.read(scan_id)
                except ValueError:scan = None
                return self.respond(200, scan) if scan else self.respond(404, {'error': 'Scan not found.'})
            return super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path != '/api/scans':return self.respond(404, {'error': 'Not found.'})
            if not self.allowed():return self.respond(403, {'error': 'Origin is not permitted.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond(415, {'error': 'Use application/json.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2048:raise ValueError('Invalid request size.')
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):raise ValueError('Invalid request.')
                concept_id = payload.get('conceptId')
                concept = get_concept(concept_id) if concept_id is not None else None
                keyword = concept['label'] if concept else normalize_keyword(payload.get('keyword'))
                countries = normalize_countries(payload.get('countries', CONCEPT_COUNTRIES if concept else DEFAULT_COUNTRIES))
                refresh = payload.get('refresh', False)
                if type(refresh) is not bool:raise ValueError('Invalid refresh option.')
            except (ValueError, TypeError):return self.respond(400, {'error': 'Enter a keyword and choose up to eight supported countries.'})
            active = manager.active(keyword, countries, concept_id)
            if active:return self.respond(202, {'scan': active, 'cached': False})
            cached = manager.cached(keyword, countries, concept_id)
            if cached and not refresh:return self.respond(200, {'scan': cached, 'cached': True})
            if not gate.acquire(blocking=False):return self.respond(409, {'error': 'A scan is already running. Wait for it to finish.'})
            try:
                scan = manager.create(keyword, countries, concept_id)
                def run():
                    try:manager.run(scan['id'])
                    finally:gate.release()
                executor.submit(run)
            except ValueError as error:
                gate.release()
                return self.respond(422, {'error': str(error)})
            except Exception:
                gate.release()
                return self.respond(503, {'error': 'The local collector is unavailable.'})
            return self.respond(202, {'scan': scan, 'cached': False})

        def log_message(self, format, *args):
            # Avoid logging user queries or request bodies.
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Local geographic keyword scans and cached site hosting')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--directory', default='out')
    args = parser.parse_args()
    manager = ScanManager(Settings.load())
    # A terminated process cannot truthfully keep showing an active scan.
    for path in manager.root.glob('*.json'):
        scan = json.loads(path.read_text())
        if scan['status'] in {'queued', 'running'}:
            scan.update(status='partial' if scan.get('recording') else 'failed', error='The local worker stopped before completing this scan.')
            scan.pop('active', None)
            manager.save(scan)
            if scan['status'] == 'partial':manager.publish(scan)
    with ThreadPoolExecutor(max_workers=1) as executor:
        handler = make_handler(manager, executor, threading.Lock(), args.directory, args.port)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
        print(f'Worldview scan service: http://127.0.0.1:{args.port} (one bounded scan at a time)', flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()


if __name__ == '__main__':main()
