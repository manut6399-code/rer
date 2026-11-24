# 🧬 Architecture & internals

For when you want to change the ranking, add a source, or understand why a repo landed in a section.

---

## 1. Data flow

```
                    ┌──────────────────────────────────────────────┐
                    │  GitHub public REST Search API               │
                    │  /search/repositories  ·  /search/users      │
                    └───────────────────┬──────────────────────────┘
                                        │  (paced, retried, TLS, allowlist)
   ┌──────────────────────────┐        ▼
   │ github.com/trending      │   ┌──────────────────────────────┐
   │ github.com/trending/     ├──▶│ sources.collect()            │
   │   developers  (HTML)     │   │  → Collection                │
   └──────────────────────────┘   │    repos / developers /      │
                                  │    warnings / stats          │
   ┌──────────────────────────┐   └───────────────┬──────────────┘
   │ fixtures/live_snapshot   │                   │
   │ (offline DEMO source)    ├───────────────────┤
   └──────────────────────────┘                   ▼
                                  ┌──────────────────────────────┐
      ┌─────────────────────────▶│ store.py  (SQLite memory)    │
      │  previous stars,         │  repos · snapshots ·         │
      │  first-seen, seen-list,  │  digest_items · topic_history │
      │  topic baseline          │  developers                  │
      │                          └───────────────┬──────────────┘
      │                                          ▼
      │                          ┌──────────────────────────────┐
      │                          │ scoring.score_collection()   │
      │                          │  velocity → features →       │
      │                          │  4 category scores → sections│
      │                          └───────────────┬──────────────┘
      │                                          ▼
      │                          ┌──────────────────────────────┐
      │                          │ digest.Digest                │
      │                          └───────┬──────────────┬───────┘
      │                                  ▼              ▼
      │              ┌───────────────────────────┐  ┌────────────────────┐
      │              │ webapp.write_site()       │  │ notify.Notifier    │
      │              │ index.html / feed.json    │  │ Telegram/Discord/  │
      │              │ feed.xml / archive / PWA  │  │ Slack/custom       │
      │              └───────────────────────────┘  └────────────────────┘
      │                                  │
      └────────── save today's snapshots ┘
```

`pipeline.run_pipeline()` owns the whole flow. Every stage is independently replaceable: pass your own `HttpClient` (with an injected transport) or your own `Store` into `run_pipeline`.

---

## 2. Source query plan

`sources.build_search_queries(cfg, day)` builds a deterministic, rate-limit-aware plan:

| # | Label | Query shape | Signal |
|---|---|---|---|
| 1 | `new_hot` | `created:>D-N stars:>MIN fork:false archived:false` sorted by stars | already-popular newborns |
| 2 | `new_rising` | same + `pushed:>D-2`, sorted by updated | momentum |
| 3 | `hidden_gems` | `created:>D-30 stars:MIN..MAX pushed:>D-3` sorted by updated | small but active |
| 4 | `fork_magnets` | `created:>D-14 forks:>15` sorted by updated | people building on it |
| 5 | `topic_pulse` | `topic:<rotated> created:>D-N pushed:>D-3` | your niche |
| 6 | `language_pulse` | `language:"<rotated>" created:>D-N stars:>MIN` | language diversity |

Rotations use `day.toordinal() % len(list)`, so the same day always produces the same plan, and consecutive days differ. Budget: **6 queries anonymous / 10 with a token** (configurable). Trending HTML and developer search don't consume the search budget in the same way; one `search/users` call is included when enabled.

Constraints honoured (from GitHub Docs): ≤256-char query, ≤5 boolean operators, ≤1,000 results/query, `per_page=30`, `incomplete_results` surfaced as a warning.

---

## 3. Velocity — the core signal

```
measured  : (stars_today - stars_previous_snapshot) / days_elapsed   ← preferred
trending  : "N stars today" from the Trending HTML page
estimated : stars / age_in_days                                      ← day-one fallback
unknown   : 0
```

`store.previous_snapshot()` picks the newest snapshot **strictly before** today, so re-running the same day is idempotent and never pollutes the baseline. `pipeline` saves one snapshot per repo per day after scoring.

---

## 4. Scoring (deterministic, explainable)

Features, each in `[0,1]`:

```
momentum   = log10(1 + velocity)  / log10(1 + 750)
popularity = log10(1 + stars)     / log10(1 + 50000)
novelty    = exp(-age_days / 10)
activity   = exp(-days_since_push / 4)
engagement = min(1, (forks / stars) * 3.5)
quality    = 0.40·description_len/90 + 0.20·has_license
           + 0.20·min(1, topics/6)  + 0.20·not(archived|fork|template)
```

Category scores (×100, clamped):

```
viral   = .42·momentum + .22·popularity + .14·engagement + .12·activity + .10·quality
newborn = .42·novelty  + .26·momentum  + .14·quality    + .18·activity
hidden  = .42·(1-log(stars))·activity·(.4+.6·engagement)
        + .18·activity + .15·engagement + .15·novelty + .10·quality
weird   = .45·engagement + .25·novelty + .20·activity + .10·momentum
        + .10 if description matches the experimental-keyword regex
```

Each repo is assigned to its **best eligible** category (eligibility: velocity/trending rank for viral, age window for newborn, star ceiling for hidden, fork ratio or odd keywords for weird). A repo appears in **exactly one** section. `repo.score = max(category scores)`; `repo.reasons` carries human-readable evidence ("+312 stars/day (measured vs last snapshot)", "fork/star ratio 0.31").

**No machine learning, no randomness, no hidden calls** — you can explain every pick to your audience.

### No-repeat memory

`store.was_posted_within(full_name, day, suppress_days=7)` removes anything posted in the last 7 days. If a thin day leaves fewer than `items_per_section` fresh candidates the rule is relaxed and this is recorded in `stats.suppressed_repeats`.

### Topic pulse

Count topics across all candidates → compare with `AVG(repo_count)` over the previous 7 days in `topic_history` → `lift = today - baseline`; `breakout = lift >= 1.5`. Saves today's counts for tomorrow.

---

## 5. SQLite schema (private, local)

```sql
repos(full_name PK, first_seen, last_seen, max_stars, times_seen)
snapshots(full_name, captured_at, captured_date, stars, forks, open_issues,
          PK(full_name, captured_date))
digest_items(digest_date, full_name, section, score, PK(digest_date, full_name))
digest_meta(digest_date PK, generated_at, total_items, sources, status)
topic_history(topic, digest_date, repo_count, PK(topic, digest_date))
developers(login PK, first_seen, last_seen, times_seen)
```

All writes parameterised, all identifiers validated, `PRAGMA integrity_check` exposed via `status` / `doctor`. File mode 0600, directory 0700, excluded from git and the zip.

---

## 6. Output contract

`site/feed.json` (schema_version `1.0`) is the single source of truth for the PWA, RSS, chat payloads and archive:

```json
{
  "schema_version": "1.0",
  "date": "2026-11-24",
  "generated_at": "...",
  "timezone": "Asia/Kolkata",
  "demo": false,
  "headline": "...",
  "total_items": 28,
  "sections": [{"key": "viral", "title": "...", "subtitle": "...", "items": [...]}],
  "topic_pulse": [{"topic": "rust", "today": 6, "baseline": 1.0, "lift": 5.0, "breakout": true}],
  "developers": [...],
  "stats": {...},
  "warnings": [...],
  "sources": [...]
}
```

Also written: `feed.xml` (RSS 2.0), `index.html` (PWA with embedded seed), `manifest.webmanifest`, `sw.js`, `icon.svg`, `status.json`, `archive/<date>.{html,md,json,csv}`, `archive/index.html`.

### Web app

- Embedded seed JSON works from `file://` with no network.
- Over HTTP it also `fetch('./feed.json', {cache:'no-store'})` (same origin) and refreshes.
- Service worker caches only same-origin GETs; cross-origin requests are ignored.
- CSP: `default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors *`.
- `frame-ancestors *` (and deliberately no `X-Frame-Options`) is required so the sandboxed in-app preview can render the page.

---

## 7. Extension points

| Want to… | Edit |
|---|---|
| Add a discovery source | `sources.collect()` — return `Collection` items; failing sources just `out.warn(...)` |
| Change the ranking | `scoring.py` — weights at the top of `score_repo()` |
| Add a section | `scoring.SECTION_ORDER` + `SECTION_META`; `digest.build_digest()` picks them up |
| Change the daily post | `digest.to_plain()`, `to_discord_payload()`, `to_markdown()` |
| Add a channel | `notify.Notifier` + `Config` fields + `.env.example` |
| Change the dashboard | `webapp.HTML_TEMPLATE` (inline CSS/JS) |
| Change the schedule | `.github/workflows/daily.yml` cron (UTC) |
| Change the niche | `.env` → `REPORADAR_TOPICS`, `REPORADAR_LANGUAGES` |

---

## 8. Failure philosophy

1. One dead source → warning, everything else continues.
2. Trending markup drift → `[]` + warning, velocity falls back to memory.
3. All sources dead → a clear error, never an empty "success" digest.
4. Notification failure → recorded in `RunResult.notifications`, digest still published.
5. Re-running the same day → same sections, one `digest_meta` row.
6. No secrets, no stack traces, no partial writes (`atomic_write` uses temp + `os.replace`).
