# 📣 The RepoRadar channel & bot playbook

Everything you need to go from "a folder of code" to **a daily channel people actually open**: setup, posting formats, automation, editorial policy, growth, moderation, troubleshooting.

Read in order. Skip nothing in Part 1. The rest is a menu — take what fits.

---

## Part 1 — Decide the shape of your channel

Pick one primary surface first. Add the others later; RepoRadar outputs all of them from the same digest.

| Surface | Best for | Setup time | Output used |
|---|---|---|---|
| **Telegram channel** | Fastest audience, mobile-native, zero hosting | 10 min | `to_plain()` → `sendMessage` |
| **Discord server** | Dev communities, threaded discussion | 10 min | `to_discord_payload()` → webhook |
| **Slack / workspace** | Team-internal radar | 10 min | `to_slack_payload()` |
| **RSS + newsletter** | Own-your-audience, email via RSS-to-email | 20 min | `feed.xml` |
| **GitHub Pages / PWA** | Searchable archive, installable on phones | 20 min | `site/` |
| **X / LinkedIn / blog** | Reach beyond devs | manual | `archive/YYYY-MM-DD.md` |

**Recommended stack:** Telegram channel (distribution) + GitHub Pages PWA (archive/search) + GitHub Actions (automation). This is fully free and needs no always-on machine.

---

## Part 2 — First 15 minutes (local)

```bash
unzip reporadar-v1.0.0.zip && cd reporadar
python repodar.py run --demo
python repodar.py serve
```

Open `http://localhost:8080`. You should see four sections, topic chips, developer cards and a DEMO badge. Search, filter, sort, tap "Copy".

Then:

```bash
python repodar.py init                 # creates .env with 0600 permissions
python repodar.py doctor --live        # 13 checks; all must be PASS
python repodar.py secret-scan          # must say "clean"
```

`doctor --live` tests real GitHub connectivity. If it fails, check your network / firewall, not your token — public data works anonymously.

### Optional: add a GitHub token

1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained token**.
2. No repository access needed, **no scopes/permissions** — public data only. Name it `reporadar-readonly`, set a 90-day expiry.
3. Put it in `.env` as `GITHUB_TOKEN=<YOUR_TOKEN>`.
4. `chmod 600 .env` (the `init` command already does this).
5. `python repodar.py status` → `authenticated: true`. The token value is **never printed**; `status` shows only a length fingerprint.

> Never paste a token into a chat, screenshot, issue, or commit. `secret-scan` will catch credential-shaped strings in shippable files. If a token leaks, revoke it first, then rotate.

---

## Part 3 — Telegram channel (recommended)

### 3.1 Create the bot and channel

1. In Telegram, message **@BotFather** → `/newbot` → choose a name and username. Copy the token to `.env` as `TELEGRAM_BOT_TOKEN`.
2. Create a **Channel** (not a group). Make it public with a short username, e.g. `@githubradar`.
3. Add your bot as an **Administrator** of the channel with only **Post Messages** permission. Bots need admin rights to post in channels.
4. Set `TELEGRAM_CHAT_ID=@githubradar` in `.env` (a numeric `-100...` id also works).

### 3.2 Getting a numeric chat id (only if you need one)

Forward any channel post to **@userinfobot**, or call `getUpdates` after posting a message. For public channels `@username` is simpler and works immediately.

### 3.3 Test — dry run first

```bash
python repodar.py notify-test          # dry run: no message is sent
python repodar.py run --dry-run        # builds digest + shows what WOULD be sent
python repodar.py notify-test --send   # one harmless test line
```

Expected: a single message "🛰️ RepoRadar test message — your channel is connected."

### 3.4 Go live

```bash
python repodar.py run --notify
```

`--notify` is **explicit and required**. Without it, nothing is ever sent, even if credentials are in `.env`. Messages are plain text (no `parse_mode`), split at **4,096 characters**, link previews disabled, and `@everyone`-style pings impossible.

### 3.5 Post template (what your audience sees)

```
🛰️ REPORADAR · 2026-11-24
LIVE | 28 picks

🔥 Viral & Fast-Moving
• owner/repo · 8,855★ · +1,142/d
  One-line description from the maintainer
  https://github.com/owner/repo

💎 Hidden Gems
• small/thing · 180★ · +22/d
  ...

📡 #rust, #mcp, #imgui
🧠 @ada, @grace
Public data · verify before sharing
```

**Editorial upgrade:** add one human sentence at the top each day ("Today's theme: everyone is rewriting things in Rust"). That single line is what makes a bot feel like a publication.

---

## Part 4 — Discord / Slack

### Discord

1. Channel → Edit → Integrations → **Create Webhook**. Copy the URL into `.env` as `DISCORD_WEBHOOK_URL`.
2. RepoRadar sends one message with up to 4 embeds (one per section), respecting the 2,000-char `content` limit, 10 embeds/message and 6,000-char embed total. `allowed_mentions.parse` is empty → **no accidental mass pings**.
3. `python repodar.py notify-test --send`, then `python repodar.py run --notify`.

### Slack

1. Create an **Incoming Webhook** for the channel → `SLACK_WEBHOOK_URL`.
2. RepoRadar sends plain text with `unfurl_links: false` so a wall of link previews doesn't flood the channel.

### Custom webhook (advanced)

`CUSTOM_WEBHOOK_URL` is **blocked by default**. To allow it, set `REPORADAR_ALLOW_CUSTOM_WEBHOOK_HOST=1` after reviewing the host. Even then: HTTPS only, no embedded credentials, no non-default ports, and DNS must resolve to a **public** IP — loopback/private/link-local addresses are rejected (SSRF protection). Only a small summary (date, headline, top 12 repos) is sent, never your database.

---

## Part 5 — Fully automatic daily posting (zero maintenance)

`.github/workflows/daily.yml` is already included.

1. Create a **public** GitHub repo and push this folder to the default branch.
2. Settings → Secrets and variables → Actions → add only what you use:
   - `RR_GITHUB_PAT` (optional, no scopes)
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `DISCORD_WEBHOOK_URL`, `SLACK_WEBHOOK_URL`
3. Settings → Pages → **Deploy from branch** → `main` / `docs`.
4. Actions tab → **Daily RepoRadar** → **Run workflow** (manual test).
5. Check: Actions run green → `docs/index.html` updated → channel post arrived.

Schedule is `cron: '37 2 * * *'` = **02:37 UTC = 08:07 IST**, deliberately off the top of the hour to avoid GitHub's scheduler congestion. Change it in the YAML if you want a different time (cron is always UTC; IST = UTC + 5:30).

The workflow:
- uses the bundled stdlib code (no `pip install` runtime),
- sets `REPORADAR_SITE_DIR=docs` so the PWA is published to Pages,
- calls `python repodar.py run --notify`,
- only commits `docs/` (never `.env`, never `data/`, never secrets),
- uses a `concurrency` group so two runs can't overlap,
- has `permissions: contents: write` and nothing else.

> Scheduled workflows can be delayed during high load, and GitHub may disable them in a public repo after long inactivity. Glance at the Actions tab weekly. There is an external-missed-run idea in Part 11.

### Local scheduling instead

```bash
# Linux/macOS crontab: 08:07 IST daily (system timezone must be IST)
7 8 * * * cd /path/to/reporadar && /usr/bin/python3 repodar.py run --notify >> run.log 2>&1
```

Windows: Task Scheduler → `scripts\run_daily.bat`. Android/Termux: `termux-job-scheduler` or a cron from `scripts/termux.sh`.

---

## Part 6 — The PWA on mobile & desktop

`site/` is a static, installable web app:

- **No CDN, no external fonts, no analytics.** All CSS/JS is inline. CSP blocks third-party loading.
- **Works offline** after the first visit (`sw.js` caches the shell + feed on the same origin).
- **Installable**: Chrome/Edge → "Install app"; iOS Safari → Share → "Add to Home Screen".
- **Search, filter chips, sorting** by score / stars-per-day / total stars / newest.
- **Share** (Web Share API) and **Copy digest** buttons.
- **RSS / JSON / archive links** in the footer.

Serving options:

| Option | Command |
|---|---|
| Local machine | `python repodar.py serve --port 8080` |
| Phone on same Wi-Fi | `python repodar.py serve --host 0.0.0.0`, open `http://<YOUR_LAN_IP>:8080` |
| Localhost only | `python repodar.py serve --host 127.0.0.1` |
| Public | push `site/` to GitHub Pages / Netlify / Cloudflare Pages |

On Android/Termux you can run the server and the browser on the same device: `localhost:8080`.

---

## Part 7 — What to actually post (editorial system)

A raw ranking is not a publication. Use this daily 10-minute routine:

1. **Read the top 8.** Open the GitHub links. Skim README, licence, last commit date.
2. **Cut anything suspicious**: fake stars, a README that is only a coin address, a repo with no code, "free keys", a binary blob, a repo that is clearly a homework dump, or a project whose entire pitch is a security exploit against a named company.
3. **Add one human sentence** (theme of the day).
4. **Pick one "deep dive"** — 3–5 lines on why it matters. This is the post people share.
5. **Credit the maintainer** with `@handle`. Tag the language/topic.
6. **Say what it is not**: "early", "experimental", "no docs yet". Honesty builds retention.

### Reusable formats

- **Daily (default):** 4 sections × up to 8 picks, topic pulse, developer spotlight. Controlled by `REPORADAR_ITEMS_PER_SECTION`.
- **🧵 Thread of the day:** one repo, five tweets/posts: what it does, why now, code snippet, who built it, caveats.
- **Weekly recap:** take `site/archive/*.md` for 7 days, pick the 5 repos whose star count grew most (memory has the snapshots), post "what stuck".
- **Hidden gem hour:** only the 💎 section, once a week, with a longer write-up.
- **Developer spotlight:** the 🧠 section; interview-style questions, link their popular repo.
- **Topic alert:** when `topic_pulse[].breakout` is true, post a short "everyone is building X this week" note.
- **"One weird repo"**: the 🧪 section is designed for this. Great for engagement, low stakes.

### Cadence that doesn't annoy people

- 1 digest/day, same time, same format. Telegram: `disable_notification` is off by default; consider quiet hours.
- 1 thread/week, 1 recap/week, 1 hidden-gem/week.
- Don't post duplicates: `REPORADAR_SUPPRESS_DAYS=7` already prevents repeats.

---

## Part 8 — Tuning the radar

All in `.env` (see `.env.example` for the full commented list):

| Knob | Effect |
|---|---|
| `REPORADAR_LANGUAGES` | One language rotates into the query plan each day |
| `REPORADAR_TOPICS` | One topic rotates each day — this is your niche |
| `REPORADAR_NEW_WINDOW_DAYS=7` | How old "new" can be |
| `REPORADAR_HIDDEN_WINDOW_DAYS=30` | Age window for hidden gems |
| `REPORADAR_MIN_STARS=5` | Noise floor |
| `REPORADAR_HIDDEN_MAX_STARS=400` | Ceiling for "hidden" |
| `REPORADAR_ITEMS_PER_SECTION=8` | Digest length |
| `REPORADAR_SUPPRESS_DAYS=7` | No-repeat memory |
| `REPORADAR_MAX_SEARCH_QUERIES` | Hard cap on API calls (default 6 anon / 10 with token) |
| `REPORADAR_ENABLE_TRENDING=0` | API-only, zero HTML scraping |
| `REPORADAR_TIMEZONE=Asia/Kolkata` | Digest date + "today" boundary |

**For a niche channel**, set `REPORADAR_TOPICS=llm,agent,mcp,rust,webassembly` and `REPORADAR_LANGUAGES=Python,Rust,TypeScript`. The rotation gives variety without burning your rate limit.

**For a "crazy things" channel**, raise `REPORADAR_ITEMS_PER_SECTION`, lower `REPORADAR_MIN_STARS`, and lean on the 🧪 section.

---

## Part 9 — Growth, moderation, monetisation (practical, not hype)

- **Name the promise in the channel bio:** "3 new GitHub repos a day, verified by a human. No spam."
- **Pin a post** explaining the four sections and the scoring reasons.
- **Ask for replies**: "which one would you actually use?" Telegram discussion groups / Discord threads turn a broadcast into a community.
- **Cross-post deliberately**, not automatically: a weekly recap on X/LinkedIn with one link back to the archive.
- **Let people subscribe without Telegram**: RSS + Pages archive. Own the archive even if a platform changes.
- **Moderation:** disable comments for the first week if you can't watch them; add a slow mode; delete coin/airdrop spam instantly; never let a bot reply to DMs.
- **Monetisation later:** sponsorship slot in the weekly recap (clearly labelled), a paid "deep dive" tier, a job board for maintainers, consulting. Do not put ads in the daily digest — it kills trust.
- **Credit and licence:** link the repo, name the author, respect the repo's licence if you quote code. RepoRadar itself is MIT, so you can rebrand freely.

---

## Part 10 — Troubleshooting

| Symptom | Fix |
|---|---|
| `no repositories collected` | Network blocked, or search rate limit hit. Wait a minute, or add a token. `python repodar.py run --demo` should still work. |
| `source X unavailable: HTTP 403` | Rate limited. RepoRadar already waits for `Retry-After`; reduce `REPORADAR_MAX_SEARCH_QUERIES` or add a token. |
| `trending page markup changed (0 rows parsed)` | GitHub changed HTML. Digest still works via search + memory; update the regexes in `trending.py` or use `--no-trending`. |
| Telegram `chat not found` | Bot isn't an admin, or the channel username is wrong. Use `@channelusername` exactly. |
| Telegram `message is too long` | Should not happen; `to_plain()` splits at 4,096 chars. If you customised it, keep `split_text()`. |
| Discord 400 | Payload too big. Reduce `REPORADAR_ITEMS_PER_SECTION`; the builder already caps fields. |
| `custom:blocked` | Set `REPORADAR_ALLOW_CUSTOM_WEBHOOK_HOST=1` **and** use a public HTTPS host. |
| PWA shows old data | Service worker cache. Hard-refresh, or bump `CACHE` in `sw.js`. `feed.json` is fetched with `cache: no-store`. |
| Preview shows nothing | Run `python repodar.py run --demo` first; `serve` needs `site/index.html`. |
| `.env` permission warning | `chmod 600 .env` (Windows: restrict the file's ACL). |
| Database corrupted | Rare. `python repodar.py status` shows `integrity`. Delete `data/memory.db` — it rebuilds; you only lose history, not code. |
| Actions workflow didn't run | Workflow must be on the default branch; scheduled runs can be delayed; check for repo inactivity. |

---

## Part 11 — Reliability checklist for a real publication

- [ ] `doctor --live` → all PASS before the first post.
- [ ] `secret-scan` → clean, on every commit (CI enforces it).
- [ ] `notify-test --send` → one test message, then delete it.
- [ ] Manual `run --notify` → verify the actual formatting in the channel.
- [ ] GitHub Pages shows the same date as the channel post.
- [ ] Token expiry on your calendar (90 days).
- [ ] A human reviews the top 8 before enabling fully automatic posting.
- [ ] Weekly: glance at Actions, open one random repo from the archive.
- [ ] Add an external missed-run alert (e.g. a free uptime monitor pinging your Pages `status.json`) if the daily post is business-critical.

---

## Part 12 — Legal / courtesy

- Only **public** GitHub data is used. No private repos, no authenticated scraping.
- Keep request volume low (6–10 searches/day + 2 HTML pages). Honour rate limits and `robots.txt`.
- GitHub Trending is a website, not an API. If GitHub objects to your usage, switch to `--no-trending` (the API-only mode is fully functional).
- Don't imply GitHub endorsement. Don't repost README code without respecting its licence.
- If you feature a developer, link their profile and be accurate; remove a spotlight on request.

---

**You now have the whole system.** Start with Part 1–3 today; automate with Part 5 tomorrow; refine with Part 7 for the next month.
