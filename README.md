# 🛰️ RepoRadar — daily GitHub discovery engine

**Find new repos, hidden gems, viral movers, breakout topics and the developers behind them — every day — then publish a digest to your channel, feed, or phone.**

Built as a complete, self-contained workspace. Extract the zip, run one command, and you have a working radar. No `pip install`, no API keys required to start, no server required, no tracking, no telemetry.

> One honest correction: no repository has "billions of stars". GitHub's biggest projects are in the hundreds of thousands. RepoRadar ranks by **star velocity**, freshness, engagement and oddness instead — which is what actually makes a repo interesting to an audience.

---

## 60-second start

```bash
unzip reporadar-v1.0.0.zip
cd reporadar
python repodar.py run --demo     # offline demo using a bundled REAL public snapshot
python repodar.py serve          # open http://localhost:8080
```

`--demo` needs **no network and no token**. It builds the full dashboard, JSON feed, RSS, Markdown, CSV and archive from a real public GitHub snapshot captured on 2026-11-24 (dates are shifted to today, so it always looks fresh). It is clearly labelled DEMO everywhere.

For live data:

```bash
python repodar.py init           # creates a private .env (chmod 600)
python repodar.py doctor --live  # verify config + GitHub connectivity
python repodar.py run            # live public GitHub data
```

A `GITHUB_TOKEN` is **optional**. Without one you get 10 search requests/minute; with a no-scope fine-grained token you get 30/minute. RepoRadar paces requests automatically and honours `Retry-After` / `X-RateLimit-Reset`.

---

## What you actually get

| Capability | How it works |
|---|---|
| 🆕 **New repos** | GitHub search `created:>DATE`, `pushed:>DATE`, `fork:false archived:false` |
| 🔥 **Viral / fast-moving** | Measured star deltas from your own SQLite snapshots + `stars today` from GitHub Trending |
| 💎 **Hidden gems** | Low star count but active pushes, real forks, licence, topics, good description |
| 🧪 **Weird & wonderful** | High fork/star ratio + odd/experimental keyword signals |
| 📡 **Topic pulse** | Topic frequency today vs. a rolling 7-day baseline — catches breakouts |
| 🧠 **Crazy developers** | Trending developers page + search for newly created accounts with followers |
| 🧠 **Memory** | SQLite: star snapshots, first-seen dates, 7-day no-repeat suppression, topic history |
| 📱 **Mobile + desktop** | Installable PWA with offline cache; also a local read-only web server |
| 📰 **Feeds** | `feed.json`, `feed.xml` (RSS), Markdown, CSV, dated HTML archive |
| 🤖 **Bot / channel** | Telegram, Discord, Slack, custom webhook — dry-run by default |
| ⏰ **Daily automation** | GitHub Actions cron → digest → GitHub Pages → channel post |
| 🔒 **Security** | Zero dependencies, secret redaction, SSRF allowlist, XSS escaping, path traversal guards, 0600 secrets |

---

## Commands

```bash
python repodar.py init                  # .env (0600) + private data dir + site dir
python repodar.py run --demo            # offline demo, bundled real snapshot
python repodar.py run                   # live, public GitHub data
python repodar.py run --notify          # live + post to configured channels
python repodar.py run --dry-run         # prepare notifications, send nothing
python repodar.py run --date 2026-11-25 --max-queries 4 --no-trending
python repodar.py serve --port 8080     # dashboard on phone/PC/LAN
python repodar.py status                # memory stats + redacted config
python repodar.py doctor --live         # 13 health + security checks
python repodar.py secret-scan           # refuse to ship credentials
python repodar.py notify-test --send    # verify channel credentials
python repodar.py selftest              # 116 offline tests
python repodar.py --version
```

`python repodar.py --help` shows all flags. `python -m reporadar` also works if `src/` is on `PYTHONPATH`.

---

## Where things are

```
repodar.py                 ← single entry point (no install needed)
src/reporadar/
  config.py                ← env + .env validation, redacted reporting
  security.py              ← redaction, SSRF allowlist, escaping, safe paths, secret scan
  http.py                  ← hardened stdlib HTTP client (TLS, retries, rate limits)
  sources.py               ← search query plan, Trending, developers, offline demo
  trending.py              ← defensive HTML parser for GitHub Trending
  models.py                ← normalised Repo / Developer / Collection
  store.py                 ← SQLite memory (snapshots, suppression, topic history)
  scoring.py               ← explainable velocity + novelty + engagement scores
  digest.py                ← JSON / Markdown / CSV / RSS / Telegram / Discord / Slack
  webapp.py                ← installable PWA dashboard (all inline, offline cache)
  notify.py                ← channel delivery, safe-by-default
  server.py                ← read-only static server (0.0.0.0 for phone/LAN)
  pipeline.py              ← orchestration
  cli.py                   ← all commands
fixtures/live_snapshot.json  ← bundled real public data for offline demo
site/                      ← generated dashboard + feeds (regenerate any time)
data/memory.db             ← your private local memory (gitignored, 0600)
tests/                     ← 116 offline tests, 43 subtests
.github/workflows/         ← daily cron + CI
scripts/                   ← Linux/macOS/Windows/Termux launchers
```

Read next: **[GUIDE.md](GUIDE.md)** (the full bot/channel playbook), **[SECURITY.md](SECURITY.md)**, **[ARCHITECTURE.md](ARCHITECTURE.md)**, **[RESEARCH.md](RESEARCH.md)**, **[TESTING.md](TESTING.md)**.

---

## Runs on

| Device | How |
|---|---|
| Windows | `python repodar.py run` in PowerShell, `scripts\run_daily.bat` for scheduling |
| macOS / Linux | `python3 repodar.py run`, `scripts/run_daily.sh`, cron/systemd timer |
| Android | Termux: `pkg install python`, `sh scripts/termux.sh`, then `python repodar.py serve` — open `localhost:8080` in the browser, or install the PWA |
| iPhone / any mobile | Deploy `site/` to GitHub Pages / Netlify / any static host → open → "Add to Home Screen" |
| No device at all | GitHub Actions runs daily with zero maintenance and publishes to Pages + your channel |

---

## Design principles

1. **Public data only.** No private repos, no user emails, no PII beyond public GitHub handles.
2. **Signals, not endorsements.** Every pick has visible numeric reasons. A high score means "worth a look", not "safe" or "good". Verify before you post.
3. **Nothing leaves your machine unless you say so.** No analytics, no telemetry, no auto-posting. `--notify` is explicit.
4. **Zero third-party runtime dependencies.** Nothing to install, nothing to audit, no supply-chain surface. Dev tools (`pytest`, `ruff`, `bandit`) are optional and not shipped as runtime deps.
5. **Degrade gracefully.** If Trending markup changes or one search times out, you still get a digest plus a warning.

---

## Known limits (read this)

- GitHub Trending has **no official API**; the parser reads the public HTML page and is designed to return `[]` + a warning if GitHub changes the markup. You can disable it with `--no-trending`.
- GitHub Search returns **at most 1,000 results per query**, has a **256-character / 5-operator** query limit, and can return `incomplete_results`. The query plan stays inside these limits and surfaces a warning when GitHub times out.
- A repo's "stars/day" on day one is an estimate (stars ÷ age, or Trending's "stars today"). From day two it is **measured** from your own snapshot history.
- Trending scraping should stay low-volume: one request/day by default. Respect GitHub's [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
- Scheduled GitHub Actions can be delayed under load and may be disabled after long repo inactivity. Check the Actions tab occasionally.
- Spam, malware, crypto pump schemes and joke repos do appear in public search results. RepoRadar ranks them; **your editorial review is the final filter**. See GUIDE.md.

---

## License

MIT — see [LICENSE](LICENSE). You can rebrand it, sell a newsletter built on it, or fork it. Don't claim GitHub endorses it.
