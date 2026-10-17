from datetime import datetime
from pathlib import Path
import pytest

from collector.briefing.models import previous_week, validate_signal
from collector.briefing.config import load_catalog, matching_lenses


def sample(**changes):
    return dict(id='one', canonicalUrl='https://example.com/story', source='example',
                sourceType='rss', publishedAt='2026-10-14T00:00:00Z',
                collectedAt='2026-10-18T00:00:00Z', title='A development',
                excerpt=None, authorOrPublisher='Example', lensCandidates=['all'],
                matchedQueries=[], metrics={}, evidenceUrls=[], evidenceKind='factual',
                publisherGroup='example', **changes)


def test_previous_week_uses_singapore_boundary():
    start, end = previous_week(datetime.fromisoformat('2026-10-19T00:30:00+08:00'))
    assert start.isoformat() == '2026-10-12T00:00:00+08:00'
    assert end.isoformat() == '2026-10-19T00:00:00+08:00'


@pytest.mark.parametrize('field,value', [
    ('publishedAt', '2026-10-14'), ('publishedAt', '2026-10-20T00:00:00Z'),
    ('canonicalUrl', 'javascript:alert(1)'), ('canonicalUrl', 'https://user:pass@example.com'),
    ('canonicalUrl', 'https://example.com/?api_key=private'),
    ('lensCandidates', ['finance']), ('metrics', {'views': True}),
    ('metrics', {'views': float('nan')}), ('title', ''),
])
def test_invalid_signal_rejected(field, value):
    data = sample(); data[field] = value
    with pytest.raises(ValueError):
        validate_signal(data)


def test_half_open_window():
    start, end = previous_week(datetime.fromisoformat('2026-10-19T00:30:00+08:00'))
    data = sample(); data['publishedAt'] = start.isoformat()
    assert validate_signal(data, window=(start, end)).id == 'one'
    data['publishedAt'] = end.isoformat(); data['collectedAt'] = end.isoformat()
    with pytest.raises(ValueError):
        validate_signal(data, window=(start, end))


def test_tech_concepts_and_exclusions():
    catalog = load_catalog(Path('config/briefing-lenses.json'))
    assert matching_lenses('AI infrastructure engineer hiring guide', catalog) == ['all', 'tech']
    assert matching_lenses('Bridge construction infrastructure roles', catalog) == ['all']
    assert catalog.version == load_catalog(Path('config/briefing-lenses.json')).version


@pytest.mark.parametrize('title', ['DeepSeek: DeepSeek v4.1 Flash 1017', 'Claude reveals ECDSA curve origins',
                                  'How the Claude Code team does code review', 'You could have invented transformers from memory'])
def test_ai_community_headlines_belong_in_tech(title):
    from collector.briefing.config import technology_topic
    catalog = load_catalog(Path('config/briefing-lenses.json'))
    assert matching_lenses(title, catalog) == ['all', 'tech']
    assert technology_topic(title, catalog) == 'AI & models'


@pytest.mark.parametrize('title', ['Claude Monet paintings return to Paris', 'Electrical transformers on the grid', 'Transformers movie wins award'])
def test_ambiguous_names_do_not_force_tech_membership(title):
    catalog = load_catalog(Path('config/briefing-lenses.json'))
    assert matching_lenses(title, catalog) == ['all']
