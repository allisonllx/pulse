from collector.briefing.models import validate_signal
from collector.briefing.cluster import cluster_signals
from collector.briefing.rank import rank_clusters
from test_briefing_contract import sample


def signal(identifier, title, **kwargs):
    data = sample(); data.update(id=identifier, canonicalUrl='https://example.com/' + identifier, title=title, **kwargs)
    return validate_signal(data)


def test_related_reporting_merges_but_different_versions_stay_separate():
    a = signal('a', 'Acme releases GPU serving engine 2.0')
    b = signal('b', 'Acme releases GPU serving engine 2.0', source='other', publisherGroup='other')
    c = signal('c', 'Acme releases GPU serving engine 3.0')
    assert sorted(len(c.signals) for c in cluster_signals([a, b, c])) == [1, 2]


def test_missing_metrics_do_not_boost_and_independent_reporting_does():
    a = signal('a', 'Acme releases GPU engine 2.0')
    b = signal('b', 'Acme releases GPU engine 2.0', publisherGroup='other')
    single = rank_clusters(cluster_signals([a]), 'all', '2026-10-19T00:00:00Z')[0]
    corroborated = rank_clusters(cluster_signals([a, b]), 'all', '2026-10-19T00:00:00Z')[0]
    assert single.scoreFactors['discussion'] == 0
    assert corroborated.score > single.score


def test_lens_filters_discussion_is_not_proof_and_output_is_stable():
    a = signal('a', 'Acme releases GPU engine', lensCandidates=['all', 'tech'], evidenceKind='discussion', metrics={'views': 200})
    b = signal('b', 'Music awards announced')
    ranked = rank_clusters(cluster_signals([b, a]), 'tech', '2026-10-19T00:00:00Z')
    assert len(ranked) == 1
    assert ranked[0].scoreFactors['corroboration'] == 0
    assert ranked[0].discussionBasis == 'popularity'


def test_velocity_requires_comparable_samples_and_ignores_counter_resets():
    a = signal('a', 'Acme GPU release discussion', evidenceKind='discussion', metrics={'views': 200})
    earlier = a.to_dict(); earlier.update(collectedAt='2026-10-17T00:00:00Z', metrics={'views': 100})
    ranked = rank_clusters(cluster_signals([a]), 'all', '2026-10-19T00:00:00Z', history=[earlier, a.to_dict()])
    assert ranked[0].discussionBasis == 'velocity'
    assert ranked[0].scoreFactors['discussion'] > 0
    earlier['metrics'] = {'views': 300}
    ranked = rank_clusters(cluster_signals([a]), 'all', '2026-10-19T00:00:00Z', history=[earlier, a.to_dict()])
    assert ranked[0].scoreFactors['discussion'] == 0
