# Changelog

## 1.0.0 — 2026-11-24

Initial complete release. Built, researched, tested and packaged in one session.

**Discovery**
- 6-query GitHub Search plan (new/hot, new/rising, hidden gems, fork magnets, rotating topic + language pulse).
- Defensive parser for `github.com/trending` and `github.com/trending/developers`.
- `search/users` for newly created developer accounts.
- Bundled real public snapshot for a fully offline `--demo` mode with date shifting.

**Memory & ranking**
- SQLite star snapshots → measured star velocity from day two.
- 7-day no-repeat suppression, first-seen dates, topic-history baseline & breakout detection.
- Four explainable sections (Viral, Born Recently, Hidden Gems, Weird & Wonderful) with numeric reasons and badges.

**Publishing**
- JSON feed, RSS 2.0, Markdown, CSV, dated HTML archive.
- Installable offline PWA dashboard (search, filters, sort, share, copy, CSP, no external assets).
- Telegram / Discord / Slack / opt-in custom webhook delivery, dry-run by default.
- Read-only static server for desktop/LAN/mobile.
- GitHub Actions daily cron → `docs/` Pages → channel post, plus CI workflow.

**Security**
- Zero runtime dependencies; stdlib only.
- Secret redaction, `.env` 0600, DB 0600 in 0700 dir, secret scanner, gitignore rules.
- SSRF allowlist with public-IP DNS checks on every request and redirect hop.
- XSS/CSV-injection/path-traversal/SQL-injection defences, TLS verification, rate-limit pacing.

**Verification**
- 116 tests (+43 subtests), ruff clean, bandit 0 issues, doctor 13/13, live GitHub run, HTTP smoke test.
