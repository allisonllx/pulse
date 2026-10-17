from dataclasses import dataclass, field
import hashlib
import re
from .models import Signal, timestamp


@dataclass
class Cluster:
    id: str
    signals: list[Signal] = field(default_factory=list)


def cluster_signals(signals):
    """Conservative headline matching; ambiguous developments remain separate."""
    clusters = []
    for signal in sorted(signals, key=lambda item: (item.publishedAt, item.id)):
        title = ' '.join(re.findall(r'[\w.]+', signal.title.casefold()))
        matched = None
        for cluster in clusters:
            anchor = cluster.signals[0]
            anchor_title = ' '.join(re.findall(r'[\w.]+', anchor.title.casefold()))
            same_event = len(title.split()) >= 5 and title == anchor_title and abs((timestamp(signal.publishedAt) - timestamp(anchor.publishedAt)).total_seconds()) <= 3 * 86400
            if signal.canonicalUrl == anchor.canonicalUrl or same_event:
                matched = cluster
                break
        if matched is None:
            matched = Cluster(hashlib.sha256(title.encode()).hexdigest()[:24])
            clusters.append(matched)
        if not any(item.id == signal.id for item in matched.signals):
            matched.signals.append(signal)
    return clusters
