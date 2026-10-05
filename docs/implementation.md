# Worldview implementation ledger

Authority: the user's Worldview 11-day plan in this chat.

## Decisions

- Greenfield repository; implement here on a new implementation branch. No existing app or shared branch is being changed.
- Credentials remain in ignored `.env.local`. Pilot: 15-country News and six-country YouTube verified; Search and TikTok failures remain visible.
- Missing Vercel CLI authentication: verify connector deployment capability; use an authorized hosting fallback if needed, retaining Vercel-compatible source.
- Local scheduled six-hour collection is explicit, not silently installed as a background service. Eleven days of history and a final expiry-day harvest cannot be completed in one session.

## Task boundaries and preflight

| Task | Producer/consumer | Review |
| --- | --- | --- |
| Collector and topic engine | Python writes manifest and recording JSON; frontend reads shared contract | No shared implementation files |
| City and discovery UI | TypeScript reads recording schema; collector controls raw observations | Demo clearly separated from live data |
| Integration and release | Reads both systems; validates snapshots, build, browser, exports | Deployment excludes credentials and raw session data |

## Progress

- [x] Collection, scheduling, storage, extraction, topic analysis, export/restore
- [x] City UI, filters, timeline, comparisons, fallback
- [x] End-to-end tests and independent review
- [x] Public deployment configuration and runbook; native deployment status tracked in this chat
