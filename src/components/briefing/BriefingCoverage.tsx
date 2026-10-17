import type { WeeklyBriefing } from '@/lib/briefings';
import styles from './briefing.module.css';

export default function BriefingCoverage({ briefing }: { briefing: WeeklyBriefing }) {
  return <aside className={styles.coverage}><p className={styles.kicker}>THE VIEW BEHIND THE BRIEFING</p><h2>Source coverage</h2><p>{briefing.coverage.scope}. {briefing.coverage.note}</p><ul>{briefing.coverage.sources.map((s, i) => <li key={s.source + i}><strong>{s.source}</strong><span>{s.status}{s.itemCount !== undefined && ['success', 'partial', 'empty'].includes(s.status) ? ` · ${s.itemCount} collected` : ''}</span>{s.reason && <small>{s.reason}</small>}</li>)}</ul><p>Prepared {new Date(briefing.generatedAt).toLocaleString('en-GB', { timeZone: 'Asia/Singapore' })} SGT</p></aside>;
}
