from collections import defaultdict
import re
from .models import timestamp


def theme_for(text, lens):
    patterns = ([('AI & models', r'\b(ai|model|llm|artificial intelligence)\b'),
                 ('Infrastructure', r'\b(gpu|cloud|data center|kubernetes|infrastructure)\b'),
                 ('Security', r'\b(security|cyber|vulnerability|breach)\b'),
                 ('Developer tools', r'\b(developer|software|release|open source)\b')]
                if lens == 'tech' else
                [('Technology', r'\b(ai|software|gpu|technology|semiconductor)\b'),
                 ('Science & health', r'\b(science|health|research|medical|space)\b'),
                 ('Business', r'\b(business|economy|market|company|bank|trade)\b'),
                 ('Culture', r'\b(music|film|art|culture|sport|game|award)\b')])
    return next((label for label, expression in patterns if re.search(expression, text, re.I)), 'Tech business' if lens == 'tech' else 'World')


def compose_briefing(ranked, lens, runs, window):
    start, end = map(timestamp, window)
    themes = defaultdict(list)
    factual_rows = [row for row in ranked if any(s.evidenceKind in {'factual', 'announcement'} for s in row.cluster.signals)]
    discussion_rows = [row for row in ranked if row not in factual_rows and any(s.evidenceKind == 'discussion' for s in row.cluster.signals)]
    selected, publisher_counts = [], defaultdict(int)
    seen_themes = set()
    for row in factual_rows:
        anchor = next(s for s in row.cluster.signals if s.evidenceKind in {'factual', 'announcement'})
        theme = theme_for((anchor.authorOrPublisher or '') + ' ' + anchor.title + ' ' + (anchor.excerpt or ''), lens)
        if theme not in seen_themes:
            selected.append(row)
            publisher_counts[anchor.publisherGroup or anchor.source] += 1
            seen_themes.add(theme)
    for row in factual_rows:
        anchor = next(s for s in row.cluster.signals if s.evidenceKind in {'factual', 'announcement'})
        group = anchor.publisherGroup or anchor.source
        if row not in selected and publisher_counts[group] < 6:
            selected.append(row)
            publisher_counts[group] += 1
        if len(selected) == 12:
            break
    for row in factual_rows:
        if len(selected) >= 12:
            break
        if row not in selected:
            selected.append(row)
    selected += discussion_rows[:8]
    for row in ranked:
        if len(selected) >= 20:
            break
        if row not in selected:
            selected.append(row)
    selected.sort(key=lambda row: (-row.score, row.cluster.id))
    for row in selected:
        signals = [s for s in row.cluster.signals if start <= timestamp(s.publishedAt) < end]
        if not signals:
            continue
        factual = [s for s in signals if s.evidenceKind in {'factual', 'announcement'}]
        discussions = [s for s in signals if s.evidenceKind == 'discussion']
        # Discovery snippets alone cannot support an editorial development.
        if not factual and not discussions:
            continue
        anchor = max(factual or discussions, key=lambda s: timestamp(s.collectedAt))
        def link(s):
            return dict(url=s.canonicalUrl, title=s.title, source=s.source,
                        evidenceKind=s.evidenceKind, publishedAt=s.publishedAt, discoveryMethod=s.sourceType)
        basis = 'reported' if factual else 'community-signal'
        description = anchor.excerpt or ('Public discussion surfaced in the selected sources.' if not factual else 'The linked publisher reports this development; open the source for details.')
        themes[theme_for((anchor.authorOrPublisher or '') + ' ' + anchor.title + ' ' + (anchor.excerpt or ''), lens)].append(dict(
            id=row.cluster.id, headline=anchor.title, whyItMatters=description,
            editorialBasis=basis, publishedAt=anchor.publishedAt,
            evidenceLinks=list({s.canonicalUrl: link(s) for s in factual}.values()),
            discussionLinks=list({s.canonicalUrl: link(s) for s in discussions}.values()),
            scoreFactors=row.scoreFactors, score=row.score, discussionBasis=row.discussionBasis))
    count = sum(map(len, themes.values()))
    factual_groups = {s.publisherGroup or s.source for row in ranked for s in row.cluster.signals
                      if s.evidenceKind in {'factual', 'announcement'}}
    degraded = any(row['status'] not in {'success', 'empty'} for row in runs)
    return dict(schemaVersion=1, editionId=end.strftime('%Y-%m-%d'), windowStart=window[0], windowEnd=window[1],
                generatedAt=max((r.get('finishedAt', window[1]) for r in runs), default=window[1]), lens=lens,
                status='thin' if count < 15 or len(themes) < 4 or len(factual_groups) < 2 else 'degraded' if degraded else 'complete',
                coverage=dict(scope='Selected English-language sources', sources=runs,
                              note='Sampled source coverage; missing sources do not imply no discussion.'),
                themes=[dict(id=re.sub(r'[^a-z]+', '-', name.lower()).strip('-'), label=name, developments=items)
                        for name, items in themes.items()], methodVersion='weekly-pulse-1')
