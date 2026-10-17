import hashlib
import json
from pathlib import Path
from ..publish import atomic_write, canonical
from .models import public_url, timestamp


def publish_edition(all_briefing, tech_briefing, destination):
    root = Path(destination)
    for lens, value in [('all', all_briefing), ('tech', tech_briefing)]:
        if value['lens'] != lens or not value['themes'] or value['schemaVersion'] != 1:
            raise ValueError('Cannot publish an empty or invalid briefing')
        start, end = timestamp(value['windowStart']), timestamp(value['windowEnd'])
        if start >= end:
            raise ValueError('Invalid window')
        for theme in value['themes']:
            for item in theme['developments']:
                if not start <= timestamp(item['publishedAt']) < end:
                    raise ValueError('Item outside edition window')
                for link in item['evidenceLinks'] + item['discussionLinks']:
                    public_url(link['url'])
    if all_briefing['windowStart'] != tech_briefing['windowStart'] or all_briefing['windowEnd'] != tech_briefing['windowEnd']:
        raise ValueError('Lens windows must match')
    revision = hashlib.sha256(canonical([all_briefing, tech_briefing])).hexdigest()[:16]
    edition = timestamp(all_briefing['windowEnd']).strftime('%Y-%m-%d')
    base = f'/data/briefings/{edition}/{revision}'
    paths = dict(all=base + '/all.json', tech=base + '/tech.json')
    def immutable(path, payload):
        encoded = canonical(payload)
        if path.exists() and path.read_bytes() != encoded:
            raise ValueError('Immutable publication collision')
        if not path.exists():
            atomic_write(path, encoded)
    for lens, value in [('all', all_briefing), ('tech', tech_briefing)]:
        immutable(root / edition / revision / (lens + '.json'), dict(value, revision=revision))
    editions = []
    if (root / 'manifest.json').exists():
        previous = json.loads((root / 'manifest.json').read_text())
        index_path = previous['archiveUrl'].removeprefix('/data/briefings/')
        editions = json.loads((root / index_path).read_text())['editions']
    entry = dict(editionId=edition, revision=revision, lenses=paths)
    editions = [entry] + [e for e in editions if e['editionId'] != edition]
    editions.sort(key=lambda e: e['editionId'], reverse=True)
    index = dict(schemaVersion=1, editions=editions)
    archive_hash = hashlib.sha256(canonical(index)).hexdigest()[:16]
    archive_url = f'/data/briefings/archives/{archive_hash}.json'
    immutable(root / 'archives' / (archive_hash + '.json'), index)
    manifest = dict(schemaVersion=1, **entry, archiveUrl=archive_url)
    atomic_write(root / 'manifest.json', canonical(manifest))
    return manifest
