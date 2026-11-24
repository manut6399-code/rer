# 🔒 Security design & verification

RepoRadar was built so you can publish a daily automated feed **without creating a credential leak, an SSRF hole, an XSS hole, or a database exposure**. This document is the threat model, the controls, and the evidence.

---

## 1. What the system handles

| Data | Sensitivity | Where it lives |
|---|---|---|
| Public GitHub repo metadata | Public | `site/*.json|html|xml|md|csv` (publishable) |
| Public GitHub handles | Public | digest + SQLite |
| Star snapshots / topic history / seen-list | Public, locally derived | `data/memory.db` (0600, gitignored, **never published**) |
| `GITHUB_TOKEN`, Telegram/Discord/Slack secrets | Secret | process environment / `.env` (0600, gitignored) only |

**No private repositories, no emails, no OAuth scopes, no analytics, no telemetry, no third-party runtime packages.**

---

## 2. Threat model & controls

| # | Threat | Control | Code |
|---|---|---|---|
| T1 | Token printed in logs/errors/URLs | `redact()` on every error, URL and exception; tokens only in `Authorization` header or Telegram path, never query strings; `status` prints a length fingerprint only | `security.py`, `http.py`, `cli.py`, `notify.py` |
| T2 | Secret committed to a repo | `.gitignore` excludes `.env`, `*.db`, `data/`; `secret-scan` command + CI step fail the build on credential-shaped strings; `.env.example` has placeholders only | `.gitignore`, `security.secret_scan`, `ci.yml` |
| T3 | Secret file readable by other users | `init` writes `.env` with `atomic_write(..., private=True)` → 0600; data dir 0700; SQLite file 0600; `doctor`/`status` warn on bad permissions | `security.atomic_write`, `store.py`, `cli.py` |
| T4 | **SSRF** via a malicious/redirect URL | Outbound URLs require HTTPS, an exact host allowlist (`api.github.com`, `github.com`, or notification hosts), default port, no userinfo; DNS is resolved and **every** address must be globally routable; redirects are re-validated per hop; custom webhook hosts are opt-in and still public-IP-only | `security.validate_url`, `http._request` |
| T5 | **XSS** from a hostile repo description | All upstream strings are cleaned (control chars stripped, length capped) and HTML/XML/Markdown escaped at render time; the embedded JSON seed escapes `<`, `>`, `&` and U+2028/9 so it cannot close a `<script>` tag; CSP `default-src 'self'` + `object-src 'none'` + `base-uri 'none'`; no external scripts/fonts/images | `security.escape_*`, `digest.py`, `webapp.py` |
| T6 | **CSV / spreadsheet formula injection** | Cells beginning with `=`, `+`, `-`, `@`, tab or CR are prefixed with `'` | `digest.csv_safe` |
| T7 | **Path traversal** on the web server / exports | `safe_path()` resolves every path and proves it stays under the base; components must match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`; hidden/dot files, `..`, backslashes, absolute paths, and non-allowlisted extensions are rejected; no directory listing; read-only server (POST/PUT/DELETE → 405) | `security.safe_path`, `server.py` |
| T8 | **SQL injection** | All queries parameterised; repository slugs validated by `safe_repo_name` before any query | `store.py` |
| T9 | Database leak | SQLite lives in a 0700 `data/` dir, 0600 file, excluded from git and from the shipped zip; the web server serves only `site/` and only allowlisted extensions; `/api/status` returns only non-secret counts | `store.py`, `server.py`, packaging |
| T10 | Malicious upstream HTML/JSON | Defensive parsing: every field optional, numbers clamped, tags stripped, markup drift returns `[]` + warning instead of crashing or mis-ranking | `trending.py`, `models.py`, `sources.py` |
| T11 | Amplified API abuse / rate-limit bans | Serial requests, 6.5 s anonymous / 2.2 s authenticated pacing, `Retry-After` and `X-RateLimit-Reset` honoured, bounded exponential backoff, 1,000-result/256-char/5-operator query limits respected, incomplete results surfaced | `http.py`, `sources.py` |
| T12 | TLS downgrade / MITM | `ssl.create_default_context()` (certificate + hostname verification), HTTPS-only, redirects re-validated | `http._default_transport` |
| T13 | Accidental mass notification / spam | **Nothing is sent by default.** Requires explicit `--notify` (or `AUTO_NOTIFY=1` **and** `DRY_RUN=0`); `notify-test` is dry-run unless `--send`; `allowed_mentions: {parse: []}` on Discord; 4,096-char Telegram splitting | `notify.py`, `cli.py` |
| T14 | Response-size resource exhaustion | Hard caps on response body, payload, request URL length and served file size | `http.py`, `server.py` |
| T15 | Supply-chain / dependency CVEs | **Zero runtime dependencies** — Python standard library only. Dev tools (`pytest`, `ruff`, `bandit`) are optional, not imported by the app | `requirements.txt` (empty by design) |
| T16 | Secrets in the delivered zip | The build script excludes `.env`, `*.db`, `data/`, caches and VCS files; the final package is re-scanned with `secret-scan` | `scripts/make_zip.sh` |

---

## 3. One reviewed exception

`bandit` rule **B104** (binding to all interfaces) is skipped via `bandit.yml`:

- `serve()` binds `0.0.0.0:8080` so the dashboard works on a phone on the LAN and inside the sandboxed Arena preview.
- The server is **strictly read-only static files**: no auth, no uploads, no dynamic endpoints, no database access, no secrets on disk under `site/`.
- Use `--host 127.0.0.1` to restrict it to localhost.
- Blocking traversal, hidden files, disallowed extensions and write methods is tested.

Everything else passes bandit with **zero findings** at all severities.

---

## 4. Verification performed (2026-11-24)

| Check | Result |
|---|---|
| `python -m pytest tests -q` | **116 passed, 43 subtests passed** |
| `python repodar.py selftest` (stdlib unittest) | **116 tests, OK** |
| `ruff check src tests repodar.py` | **All checks passed** |
| `bandit -r src -q -c bandit.yml` | **0 issues** |
| `python -m compileall` | OK |
| `python repodar.py doctor` | **13/13 PASS** |
| `python repodar.py doctor --live` | GitHub API reachable |
| `python repodar.py secret-scan` | clean |
| Live end-to-end run vs real GitHub API + Trending | 8 sources, 28 picks, no warnings |
| HTTP smoke test of the static server | CSP + headers + 404/405/traversal checks pass |

Hostile-input tests specifically cover: `<script>` in descriptions, `javascript:` URLs, CSV `=HYPERLINK(...)`, SQL-injection-shaped slugs, `../` traversal, `127.0.0.1`/`localhost` SSRF, non-allowlisted redirect targets, credential-shaped strings in logs, and 401/403/429/500 responses.

See **[TESTING.md](TESTING.md)** for the full matrix.

---

## 5. Operator checklist (do this before you publish)

```bash
python repodar.py init
chmod 600 .env                     # POSIX
python repodar.py doctor --live
python repodar.py secret-scan
python repodar.py run --dry-run    # no messages sent
# only then:
python repodar.py run --notify
```

- [ ] `.env` is gitignored and 0600.
- [ ] No token in any committed file, screenshot, or log.
- [ ] GitHub token is fine-grained, no scopes, has an expiry.
- [ ] Bot token is stored only in `.env` / GitHub Actions Secrets.
- [ ] `REPORADAR_AUTO_NOTIFY=0` until a human has reviewed a few digests.
- [ ] `data/` and `*.db` are not in the zip or the repo.
- [ ] You reviewed the top picks for spam/malware before posting.

---

## 6. Reporting a vulnerability

If you find a real issue, **do not post the secret**. Open a private report with:
1. a description and reproduction steps,
2. the affected file/command,
3. a redacted log excerpt (`python repodar.py status` is safe).

For a leaked credential: **revoke/rotate first**, then investigate. Because no secret is written to disk outside `.env`, rotation is the complete remediation.

---

## 7. What this is NOT

- Not an authentication system, not a multi-user service, not a public write API.
- Not a guarantee that a repo is safe, licensed, or non-malicious — the score is a discovery signal.
- Not an excuse to hammer GitHub. Keep the daily cadence and rate limits.
