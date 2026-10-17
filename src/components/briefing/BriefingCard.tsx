import type { Development } from '@/lib/briefings';
import styles from './briefing.module.css';

export default function BriefingCard({ development: d }: { development: Development }) {
  const evidenceLabel = d.evidenceLinks.length && d.discussionLinks.length ? 'Reporting + discussion'
    : d.editorialBasis === 'community-signal' ? 'Community discussion'
    : d.evidenceLinks.every(link => link.evidenceKind === 'announcement') ? 'Announcement' : 'Reporting';
  const labels = [d.sector, ...(d.topic !== d.sector ? [d.topic] : []), evidenceLabel].join(' · ');
  return <article className={styles.card}>
    <p className={styles.cardLabel}><span>{labels}</span><time dateTime={d.publishedAt}>{new Date(d.publishedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'Asia/Singapore' })}</time></p>
    <h3>{d.headline}</h3><p className={styles.description}>{d.whyItMatters}</p>
    {d.evidenceLinks.length > 0 && <div className={styles.links}><span>Reporting & announcements</span>{d.evidenceLinks.map(l => <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer">{l.source} ↗</a>)}</div>}
    {d.discussionLinks.length > 0 && <div className={styles.links}><span>Discussion</span>{d.discussionLinks.map(l => <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer">{l.source} ↗</a>)}</div>}
    <details className={styles.reason}><summary>Why this appeared</summary><p>Ranked using recency, independent reporting, available discussion metrics, sector fit, and novelty. Discussion metrics describe {d.discussionBasis === 'velocity' ? 'growth between comparable observations' : d.discussionBasis === 'popularity' ? 'sampled popularity' : d.discussionBasis === 'mixed' ? 'a mix of growth and sampled popularity' : 'no measured engagement'}.</p><dl>{Object.entries(d.scoreFactors).map(([key, score]) => <div key={key}><dt>{key}</dt><dd>{Math.round(score * 100)}%</dd></div>)}</dl></details>
  </article>;
}
