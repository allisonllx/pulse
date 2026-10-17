from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class Catalog:
    version: str
    lenses: dict


def load_catalog(path: Path) -> Catalog:
    payload = json.loads(path.read_text())
    if payload.get('schemaVersion') != 1 or set(payload.get('lenses', {})) != {'all', 'tech'}:
        raise ValueError('Invalid lens catalog')
    for lens in payload['lenses'].values():
        for key in ('concepts', 'exclusions', 'queries', 'themes'):
            if not isinstance(lens.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in lens[key]):
                raise ValueError('Invalid lens configuration')
    version = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return Catalog(version, payload['lenses'])


def matching_lenses(text: str, catalog: Catalog) -> list[str]:
    def matches(term):
        return re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I) is not None
    tech = catalog.lenses['tech']
    return ['all', 'tech'] if any(map(matches, tech['concepts'])) and not any(map(matches, tech['exclusions'])) else ['all']
