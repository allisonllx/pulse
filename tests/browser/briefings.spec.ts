import { test, expect } from '@playwright/test';

const paths = { all: '/data/briefings/2026-10-19/abc/all.json', tech: '/data/briefings/2026-10-19/abc/tech.json' };
const edition = { editionId: '2026-10-19', revision: 'abc', lenses: paths };
const makeBriefing = (lens: string) => ({ schemaVersion: 1, editionId: edition.editionId, lens, status: 'thin', windowStart: '2026-10-12T00:00:00Z', windowEnd: '2026-10-19T00:00:00Z', generatedAt: '2026-10-19T01:00:00Z',
  coverage: { scope: 'Selected English-language sources', note: 'X is unavailable.', sources: [{ source: 'x', status: 'disabled', reason: 'Public access not verified' }] },
  themes: [{ id: 'technology', label: 'Technology', developments: [{ id: 'one', headline: lens === 'all' ? 'The week in focus' : 'A new GPU serving tool', whyItMatters: 'An official release adds GPU support.', editorialBasis: 'reported', publishedAt: '2026-10-14T00:00:00Z', scoreFactors: { recency: 0.5 }, discussionBasis: 'unavailable', evidenceLinks: [{ url: 'https://example.com/release', title: 'Release', source: 'Example', evidenceKind: 'announcement', publishedAt: '2026-10-14T00:00:00Z', discoveryMethod: 'rss' }], discussionLinks: [{ url: 'https://news.ycombinator.com/item?id=1', title: 'Discussion', source: 'Hacker News', evidenceKind: 'discussion', publishedAt: '2026-10-14T00:00:00Z', discoveryMethod: 'rss' }] }] }] });

test('weekly lenses expose evidence, source gaps and mobile layout', async ({ page }) => {
  await page.route('**/data/briefings/manifest.json', r => r.fulfill({ json: { schemaVersion: 1, ...edition, archiveUrl: '/data/briefings/archives/abc.json' } }));
  await page.route('**/data/briefings/archives/abc.json', r => r.fulfill({ json: { schemaVersion: 1, editions: [edition] } }));
  for (const lens of ['all', 'tech'] as const) await page.route('**' + paths[lens], r => r.fulfill({ json: makeBriefing(lens) }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'The week in focus' })).toBeVisible();
  await page.getByRole('button', { name: 'Technology', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'A new GPU serving tool' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Example ↗' })).toHaveAttribute('href', 'https://example.com/release');
  await expect(page.getByRole('link', { name: 'Hacker News ↗' })).toBeVisible();
  await expect(page.getByText('Public access not verified')).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
});

test('missing edition keeps the explorer accessible', async ({ page }) => {
  await page.route('**/data/briefings/manifest.json', r => r.fulfill({ status: 404 }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'No weekly briefing has been published yet.' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open the signal explorer ↗' })).toHaveAttribute('href', '/explore');
});
