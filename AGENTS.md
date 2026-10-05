<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Cursor Cloud specific instructions

`npm run dev` serves Pulse on port 3000. The script already binds `0.0.0.0`. Checked-in JSON under `public/data` opens the city: switch the country select, click a topic to focus a shop, use Compare viewpoints, and open Trends.

Offline collector checks use `.venv-collector`:

```sh
sudo apt-get install -y python3.12-venv
python3 -m venv .venv-collector
.venv-collector/bin/python -m pip install -e '.[test]'
.venv-collector/bin/python -m pytest -q
.venv-collector/bin/python -m collector collect --once --dry-run
```

`python3.12-venv` is required to create that virtualenv. Live harvesting reads Oxylabs credentials and `WORLDVIEW_BUDGET_BYTES` from an uncommitted `.env.local`. Install the `browser`, `embeddings`, or `translations` extras only when a task needs Playwright collection or local models. `npm run test:e2e` runs the browser suite and expects Playwright Chromium.
