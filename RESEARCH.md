# 🔬 Research notes (verified 2026-11-24)

The design decisions below came from live checks against GitHub plus the official documentation — not guesses. Links are included so you can re-verify when GitHub changes something.

## 1. GitHub Search API (official, primary source)

- Endpoint: `GET https://api.github.com/search/repositories`, params `q`, `sort`, `order`, `per_page`. Docs: <https://docs.github.com/en/rest/search/search#search-repositories>
- **Rate limit: 30 requests/minute authenticated, 10/minute unauthenticated.** Live response headers from this workspace confirmed `x-ratelimit-limit: 10`, `x-ratelimit-resource: search`, `x-ratelimit-remaining` decreasing on each call.
- **Max 1,000 results per search** (10 pages × 100). Queries must be **≤256 characters** and use **≤5 AND/OR/NOT operators**. Queries that time out return `incomplete_results: true`. Docs: <https://docs.github.com/en/rest/search/search#about-search>
- Search results already contain the full repository payload — no second request per repo. Live payload keys included `full_name`, `html_url`, `description`, `stargazers_count`, `forks_count`, `open_issues_count`, `language`, `topics`, `license`, `created_at`, `pushed_at`, `updated_at`, `owner`, `fork`, `archived`, `is_template`, `size`, `default_branch`, `homepage`, `score`.
- Sort options used: `stars` and `updated`. Qualifiers used: `created:>`, `pushed:>`, `stars:>`, `stars:A..B`, `forks:>`, `topic:`, `language:`, `fork:false`, `archived:false`.
- Live sanity check: `created:>2026-11-17 stars:>5` returned `total_count: 3906` with valid ISO timestamps.
- **User-Agent is mandatory** for all REST requests. Docs: <https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api>
- **Fine-grained PAT** is recommended; no scopes are needed for public repository data. Docs: <https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api>
- Best practices: serial requests, honour `Retry-After` / `X-RateLimit-Reset`, exponential backoff, don't retry missing resources. Docs: <https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api>

**Implementation:** `HttpClient` paces search calls at 6.5 s anonymous / 2.2 s authenticated, reads rate-limit headers, waits on `Retry-After`, backs off 1 s → 2 s on 5xx, caps response bodies, and never puts the token in a URL.

## 2. GitHub Trending (unofficial surface)

- There is **no official Trending API**. The public HTML page is at `https://github.com/trending?since=daily` (also `weekly`, `monthly`), and `https://github.com/trending/developers?since=daily`. Reference: <https://apify.com/themineworks/github-trending-scraper>, <https://apify.com/devilscrapes/github-trending-scraper> (both document the absence of an official API).
- Live fetch returned ~602 KB of server-rendered HTML with `<article class="Box-row">` blocks (16 repos on the day tested). Each block contains:
  - `<h2 class="h3 lh-condensed"><a href="/owner/repo">`
  - `<p class="col-9 color-fg-muted my-1 ...">description</p>`
  - `<span itemprop="programmingLanguage">Python</span>`
  - `/owner/repo/stargazers` and `/owner/repo/forks` links with comma-formatted counts
  - `"N stars today"` in a `d-inline-block float-sm-right` span
  - contributor avatars with `alt="@handle"`
- Developers page uses `<article class="Box-row d-flex">` and `<h1 class="h3 lh-condensed"><a href="/login">` plus a "Popular repo" `<h1 class="h4 lh-condensed"><a href="/login/repo">`.
- Cross-checked three scraped star counts against `GET /repos/{owner}/{repo}` — values matched exactly (e.g. 20,129 / 2,122).
- `github.com/robots.txt` does **not** disallow `/trending`. Volume is still kept to 1–2 requests/day, with a descriptive User-Agent. Policy: <https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies>

**Implementation:** `trending.py` parses defensively; markup drift yields `[]` plus a warning, and `--no-trending` gives a fully functional API-only mode.

## 3. GitHub Actions scheduling

- `on.schedule.cron` uses **five-field POSIX cron evaluated in UTC**; the workflow must be on the **default branch**. Scheduled runs can be delayed under load and can be disabled after long repository inactivity. Use a `concurrency` group and a `timeout-minutes`. Docs: <https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule>; guide: <https://cronwizard.com/github-actions-cron>
- `GITHUB_TOKEN` is created per run; keep `permissions` minimal (`contents: write` here). Secrets belong in Actions Secrets, not YAML. Reference: <https://www.python-engineer.com/posts/run-python-github-actions/>
- Chosen schedule: `'37 2 * * *'` = 08:07 IST, an off-peak minute.

**Implementation:** `.github/workflows/daily.yml` builds the digest into `docs/`, posts to configured channels, and commits **only** `docs/`. CI workflow runs tests + linters + secret scan.

## 4. Delivery channel limits

| Channel | Constraint | Source |
|---|---|---|
| Telegram `sendMessage` | `text` 1–4,096 chars after entity parsing; `parse_mode` optional; `disable_web_page_preview` supported | <https://telegram-bot-api.info/guides/telegram-bot-send-message.html>, <https://www.unipile.com/telegram-api-send-message-a-comprehensive-guide/> |
| Discord webhook | `content` ≤2,000 chars, ≤10 embeds, ≤6,000 chars total embed text, `allowed_mentions` to suppress pings, 204 on success | <https://www.svix.com/resources/guides/discord-webhook-message-format/>, <https://discord-webhook.com/en/discord-webhook-guide/> |
| Slack incoming webhook | `text` payload, `unfurl_links: false` to avoid preview floods | Slack incoming-webhook convention; verified against the pattern in <https://www.svix.com/resources/guides/how-to-make-webhook-discord/> comparisons |

**Implementation:** `digest.to_plain()` splits at 4,096, uses plain text (no parse_mode escaping pitfalls); `to_discord_payload()` caps embeds/fields and sets `allowed_mentions: {"parse": []}`; `to_slack_payload()` disables unfurls.

## 5. "Hidden gems" & "viral" — what's actually measurable

GitHub exposes **no star-history endpoint** and no per-day star counts via REST. Therefore velocity must come from one of three places:

1. **Your own daily snapshots** (most reliable) — this is why RepoRadar has SQLite memory.
2. **Trending's "stars today"** (only for repos on that page).
3. **stars ÷ age** as a day-one estimate (rough; a 2-day-old repo with 500★ looks fast).

Community tooling confirms the same approach: scrapers track `stars_gained_period` and recommend running daily to diff results because "GitHub publishes no trending API and keeps no history" (<https://apify.com/gochujang/github-trending-tracker>). Third-party search tooling also documents the 1,000-result ceiling and 10/30-per-minute search limits (<https://apify.com/retrainmap/github-repos>).

## 6. Bundled demo snapshot

`fixtures/live_snapshot.json` is a **real public** capture from 2026-11-24: 3 repository searches (30 results each), one user search (15), 16 trending repos, 25 trending developers — 203 KB, no credentials, no private data. `collect_demo()` shifts all dates relative to today so the offline demo always shows fresh-looking newborns. It is explicitly labelled DEMO in the feed, dashboard, Markdown and chat output.

## 7. Things deliberately NOT done

- No GraphQL (REST + public HTML is enough, and fewer credentials/surfaces).
- No scraping of authenticated pages, no star-history services, no paid APIs.
- No repo cloning/code execution — a repo is only ever a *link* plus metadata. This avoids executing untrusted code entirely.
- No automatic claims about safety, quality, or licence compatibility — only public signals.
