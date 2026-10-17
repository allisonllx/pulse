'use client';

import { useEffect, useState } from 'react';
import { loadBriefing, loadEditions, type Edition, type Lens, type WeeklyBriefing as Briefing } from '@/lib/briefings';
import BriefingCard from './BriefingCard';
import BriefingCoverage from './BriefingCoverage';
import styles from './briefing.module.css';

export default function WeeklyBriefing() {
  const [lens, setLens] = useState<Lens>('all');
  const [editions, setEditions] = useState<Edition[]>([]);
  const [editionId, setEditionId] = useState('');
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('scan') || params.has('demo')) {
      window.location.replace('/explore' + window.location.search);
      return;
    }
    const controller = new AbortController();
    loadEditions(controller.signal).then(items => {
      setEditions(items);
      const requested = params.get('edition');
      if (requested && !items.some(e => e.editionId === requested)) throw new Error('This archived edition is not available.');
      setEditionId(requested || items[0]?.editionId || '');
    }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const edition = editions.find(e => e.editionId === editionId);
    if (!edition) return;
    const controller = new AbortController();
    setBriefing(null); setError('');
    loadBriefing(edition, lens, controller.signal).then(setBriefing).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [editions, editionId, lens]);
  const count = briefing?.themes.reduce((sum, t) => sum + t.developments.length, 0) ?? 0;
  const formatDate = (date: string) => new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'Asia/Singapore' });
  return <main className={styles.page}>
    <header className={styles.header}><a href="/" className={styles.brand}>pulse<span>.</span></a><span className={styles.caption}>THE WEEKLY BRIEFING</span><a className={styles.explore} href="/explore">Explore signals ↗</a></header>
    <section className={styles.intro}>
      <p className={styles.kicker}>A WEEK IN FOCUS</p>
      <h1>What moved.<br /><span>What matters.</span></h1>
      <p className={styles.subtitle}>The developments shaping the week, alongside the conversations around them.</p>
      <div className={styles.toolbar}><div className={styles.lenses} role="group" aria-label="Briefing lens">{(['all', 'tech'] as const).map(value => <button key={value} aria-pressed={lens === value} onClick={() => setLens(value)}>{value === 'all' ? 'All sectors' : 'Technology'}</button>)}</div>
        {editions.length > 0 && <label className={styles.edition}>Edition <select aria-label="Edition" value={editionId} onChange={e => { setEditionId(e.target.value); window.history.replaceState(null, '', '?edition=' + encodeURIComponent(e.target.value)); }}>{editions.map(e => <option key={e.editionId} value={e.editionId}>{e.editionId}</option>)}</select></label>}
      </div>
    </section>
    <div aria-live="polite">{error ? <section className={styles.empty}><p className={styles.kicker}>BRIEFING UNAVAILABLE</p><h2>{error}</h2><p>Explore the existing recordings while the next edition is being prepared.</p><a href="/explore">Open the signal explorer ↗</a></section> : !briefing ? <p className={styles.loading}>Opening this week’s briefing…</p> : <>
      <div className={styles.metadata}><span>{formatDate(briefing.windowStart)} — {formatDate(briefing.windowEnd)} · Singapore time</span><span>{count} developments · {briefing.themes.length} themes</span></div>
      {briefing.status === 'thin' && <p className={styles.notice}>This edition has limited source or theme coverage. Read the coverage notes below.</p>}
      <nav className={styles.themes} aria-label="Weekly themes">{briefing.themes.map(t => <a href={'#' + t.id} key={t.id}>{t.label} <span>{t.developments.length}</span></a>)}</nav>
      {briefing.themes.map((theme, index) => <section className={styles.theme} id={theme.id} key={theme.id}><div className={styles.themeHeading}><span>{String(index + 1).padStart(2, '0')}</span><h2>{theme.label}</h2></div><div>{theme.developments.map(d => <BriefingCard key={d.id} development={d} />)}</div></section>)}
      <BriefingCoverage briefing={briefing} />
    </>}</div>
    <footer className={styles.footer}><span>Selected sources. A clearer perspective.</span><a href="/explore">Go deeper with the explorer ↗</a></footer>
  </main>;
}
