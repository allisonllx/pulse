from dataclasses import dataclass
from math import log1p
from .models import timestamp
from .cluster import Cluster


@dataclass
class RankedCluster:
    cluster: Cluster
    score: float
    scoreFactors: dict[str, float]
    discussionBasis: str


def rank_clusters(clusters, lens, window_end, history=None, previous=None):
    end = timestamp(window_end)
    previous_ids = {row['id'] for row in previous or []}
    candidates = [c for c in clusters if any(lens in s.lensCandidates for s in c.signals)]
    def metric_value(signal, key, value):
        earlier = [sample for sample in history or [] if sample['id'] == signal.id
                   and sample.get('source') == signal.source
                   and sample.get('metrics', {}).get(key) is not None
                   and (timestamp(signal.collectedAt) - timestamp(sample['collectedAt'])).total_seconds() >= 21600]
        if earlier:
            first = min(earlier, key=lambda sample: timestamp(sample['collectedAt']))
            delta = value - first['metrics'][key]
            hours = (timestamp(signal.collectedAt) - timestamp(first['collectedAt'])).total_seconds() / 3600
            return max(0, delta / hours), 'velocity'
        return value, 'popularity'
    distributions = {}
    for c in candidates:
        for s in c.signals:
            if s.evidenceKind == 'discussion':
                for key, value in s.metrics.items():
                    if value is not None and value > 0:
                        metric, basis = metric_value(s, key, value)
                        if metric > 0:
                            distributions.setdefault((s.source, key, basis), []).append(log1p(metric))
    result = []
    for cluster in candidates:
        evidence = [s for s in cluster.signals if s.evidenceKind in {'factual', 'announcement'}]
        groups = {s.publisherGroup or s.source for s in evidence}
        discussions = []
        discussion_bases = set()
        for s in cluster.signals:
            if s.evidenceKind != 'discussion':
                continue
            for key, value in s.metrics.items():
                if value is not None and value > 0:
                    metric, basis = metric_value(s, key, value)
                    values = distributions.get((s.source, key, basis), [])
                    if values and metric > 0:
                        discussions.append(sum(x <= log1p(metric) for x in values) / len(values))
                        discussion_bases.add(basis)
        age = max(0, (end - max(timestamp(s.publishedAt) for s in cluster.signals)).total_seconds() / 3600)
        factors = dict(recency=2 ** (-age / 72), corroboration=min(1, max(0, len(groups) - 1) / 2),
                       discussion=max(discussions, default=0), lensFit=1.0,
                       novelty=0.0 if previous is None or cluster.id in previous_ids else 1.0)
        score = sum(factors[k] * weight for k, weight in [('recency', .25), ('corroboration', .25), ('discussion', .2), ('lensFit', .2), ('novelty', .1)])
        basis = 'velocity' if discussion_bases == {'velocity'} else 'mixed' if len(discussion_bases) > 1 else 'popularity' if discussions else 'unavailable'
        result.append(RankedCluster(cluster, round(score, 6), factors, basis))
    return sorted(result, key=lambda row: (-row.score, row.cluster.id))
