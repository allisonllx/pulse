"""Shared, bounded concept bundles for comparable market discovery."""
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parent.parent / 'config/market-concepts.json').read_text())
CONCEPT_COUNTRIES = CATALOG['defaultCountries']

def get_concept(concept_id):
    if not isinstance(concept_id, str):raise ValueError('Choose a supported concept.')
    for concept in CATALOG['concepts']:
        if concept['id'] == concept_id:return {**concept, 'version': CATALOG['version']}
    raise ValueError('Choose a supported concept.')
