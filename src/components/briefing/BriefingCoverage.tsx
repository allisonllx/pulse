import type { WeeklyBriefing } from '@/lib/briefings';
import styles from './briefing.module.css';

export default function BriefingCoverage({ briefing }: { briefing: WeeklyBriefing }) {
  const labels: Record<string, string> = { success: 'Connected', partial: 'Partial results', empty: 'No dated results', unavailable: 'Not connected', disabled: 'Not configured', failed: 'Collection failed' };
  return <aside className={styles.coverage}><p className={styles.kicker}>THE VIEW BEHIND THE BRIEFING</p><h2>Source coverage</h2><p>{briefing.coverage.scope}. {briefing.coverage.note}</p><ul>{briefing.coverage.sources.map((s, i) => <li key={s.source + i}><strong>{s.source}</strong><span>{labels[s.status] ?? s.status}{s.itemCount !== undefined && ['success', 'partial', 'empty'].includes(s.status) ? ` · ${s.itemCount} collected` : ''}</span>{s.reason && <small>{s.status === 'unavailable' && ['x', 'reddit'].includes(s.source) ? 'Connect an authorized Chrome session to enable this source.' : s.reason}</small>}</li>)}</ul><p>Prepared {new Date(briefing.generatedAt).toLocaleString('en-GB', { timeZone: 'Asia/Singapore' })} SGT</p></aside>;
}
