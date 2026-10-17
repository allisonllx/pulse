import json
import pytest
from collector.briefing.compose import compose_briefing
from collector.briefing.publish import publish_edition
from collector.briefing.cluster import cluster_signals
from collector.briefing.rank import rank_clusters
from test_briefing_ranking import signal


def briefing(lens='all'):
    items = [signal('a', 'Acme releases GPU engine', lensCandidates=['all', 'tech'])]
    ranked = rank_clusters(cluster_signals(items), lens, '2026-10-19T00:00:00Z')
    return compose_briefing(ranked, lens, [{'source': 'example', 'status': 'success'}],
                            ('2026-10-12T00:00:00Z', '2026-10-19T00:00:00Z'))


def test_thin_edition_has_typed_links_and_no_filler():
    value = briefing()
    assert value['status'] == 'thin'
    assert len(value['themes'][0]['developments']) == 1
    assert value['themes'][0]['developments'][0]['evidenceLinks'][0]['url'] == 'https://example.com/a'


def test_immutable_publication_and_failure_preserves_last_good(tmp_path):
    first = publish_edition(briefing(), briefing('tech'), tmp_path)
    before = (tmp_path / 'manifest.json').read_bytes()
    assert publish_edition(briefing(), briefing('tech'), tmp_path) == first
    assert (tmp_path / 'manifest.json').read_bytes() == before
    bad = briefing(); bad['themes'] = []
    with pytest.raises(ValueError):
        publish_edition(bad, briefing('tech'), tmp_path)
    assert (tmp_path / 'manifest.json').read_bytes() == before
    index = json.loads((tmp_path / first['archiveUrl'].removeprefix('/data/briefings/')).read_bytes())
    assert len(index['editions']) == 1


def test_busy_discussion_source_cannot_crowd_out_available_reporting():
    items = [signal('news' + str(i), 'Reported development number ' + str(i), lensCandidates=['all', 'tech']) for i in range(15)]
    items += [signal('post' + str(i), 'Community post number ' + str(i), evidenceKind='discussion', metrics={'views': 1000}) for i in range(20)]
    ranked = rank_clusters(cluster_signals(items), 'all', '2026-10-19T00:00:00Z')
    value = compose_briefing(ranked, 'all', [], ('2026-10-12T00:00:00Z', '2026-10-19T00:00:00Z'))
    selected = [d for t in value['themes'] for d in t['developments']]
    assert sum(bool(d['evidenceLinks']) for d in selected) == 12
    assert sum(d['editorialBasis'] == 'community-signal' for d in selected) == 8


def test_ai_discussion_keeps_both_technology_and_evidence_labels():
    items = [signal('claude', 'How the Claude Code team does code review', evidenceKind='discussion', lensCandidates=['all', 'tech'])]
    value = compose_briefing(rank_clusters(cluster_signals(items), 'tech', '2026-10-19T00:00:00Z'), 'tech', [], ('2026-10-12T00:00:00Z', '2026-10-19T00:00:00Z'))
    assert value['themes'][0]['label'] == 'AI & models'
    item = value['themes'][0]['developments'][0]
    assert item['sector'] == 'Technology'
    assert item['topic'] == 'AI & models'
    assert item['editorialBasis'] == 'community-signal'


def test_available_video_discussion_is_not_crowded_out_by_one_forum():
    items = [signal('news' + str(i), 'Reported story ' + str(i)) for i in range(12)]
    items += [signal('hn' + str(i), 'Forum story ' + str(i), evidenceKind='discussion', source='hacker-news', publishedAt='2026-10-17T00:00:00Z', metrics={'views': 1000}) for i in range(10)]
    items += [signal('video', 'GPU video guide', source='youtube', sourceType='youtube', evidenceKind='discussion', metrics={'views': 500})]
    ranked = rank_clusters(cluster_signals(items), 'all', '2026-10-19T00:00:00Z')
    value = compose_briefing(ranked, 'all', [], ('2026-10-12T00:00:00Z', '2026-10-19T00:00:00Z'))
    assert any(link['source'] == 'youtube' for theme in value['themes'] for d in theme['developments'] for link in d['discussionLinks'])
