# Source-fetch toolkit — data collection & literature survey

One command that gets a primary document (web page, PDF, paper, EU act) as text, trying a fixed ladder
of free routes and logging every attempt. Built 2026-10-25 after a 20-post source audit of the
masaladeutsch blog, where most "could not be opened" gaps turned out to be reachable by another route.

```bash
fetch_source.py "<url | doi:10.x/y | celex:32023R0956 | arxiv:2605.19337>" --out ./sources
```

Output: `<stem>.pdf|html`, `<stem>.txt` (extracted text) and `<stem>.log.jsonl` (every route tried, status,
result) in `--out`, plus a JSON summary on stdout (`ok`, `route`, `url`, `chars`, `blocked_hosts`,
`abstract_only`). Exit 0 = content, 2 = unavailable everywhere. Code: `~/bin/fetch_source.py` (stdlib only;
uses `pdftotext` and, for JavaScript-rendered pages, Obscura at `~/.local/share/obscura/obscura`).

## The ladder

| Step | Route | When it is used |
|---|---|---|
| 1 | Direct GET, browser User-Agent, cookie jar | Always first. HTML → text, PDF → `pdftotext -layout` |
| 2 | Obscura headless browser (standard build) | Only when the page loads but is nearly empty, i.e. needs JavaScript |
| 3a | `doi:` → OpenAlex locations → Crossref | Repository / open-access copies first, publisher last; Crossref abstract as a last resort (flagged `abstract_only`) |
| 3b | `celex:` or any EUR-Lex link → EU Publications Office (CELLAR) | Always, instead of EUR-Lex (which shows a robot check) |
| 3c | `arxiv:` → arxiv.org pdf, then abs | |
| 4 | Wayback Machine (`id_` raw snapshot) | When every live route failed |

## The one hard rule

**A bot challenge is a stop sign, not an obstacle.** CAPTCHA, "verify you're not a robot", Cloudflare /
Akamai / AWS-WAF / "Client Challenge" pages and login walls are logged as `BLOCKED` and that host is not
retried. The toolkit never impersonates browser TLS fingerprints, uses a stealth browser build, rotates
IPs or identities, or solves challenges. It looks for the *same document elsewhere* (official API,
repository copy, mirror, Wayback). If nothing works, report the source as unavailable — never cite it
from a search snippet as though it had been read.

Also: about 1 request per second per host (built in), no bulk crawling, and respect robots/terms of the
site. `--insecure` (skip TLS checks) only for government hosts with broken certificate chains.

## Proven alternate routes (verified 2026-10-25 unless dated)

| Blocked or awkward | Use instead |
|---|---|
| EUR-Lex (robot check) | `celex:<CELEX>` → `http://publications.europa.eu/resource/celex/<CELEX>` with `Accept: application/xhtml+xml` |
| Springer / Wiley / Elsevier article pages | `doi:<doi>` → OpenAlex `locations` → institutional repository PDF (e.g. Hattori 2010 via kitami-it.repo.nii.ac.jp) |
| Semantic Scholar API 429 | OpenAlex `https://api.openalex.org/works/doi:<doi>` (no key, polite) |
| Economic Times, The Hindu, BusinessLine | plain GET works (WebFetch is blocked there) |
| PIB | plain GET, follow redirects (POST breaks on its 301) |
| India Gazette | egazette.gov.in PDFs; curl/urllib works where Node TLS fails |
| data.gov.in | `www.data.gov.in/backend/dataapi/v1/resource/<id>` (api.data.gov.in is dead) |
| TradeStat | POST works if you re-GET the page for a fresh `_token` before each POST |
| Some `.gov.in` hosts | `--insecure` (bad TLS chains) |
| Indian Kanoon (403) | LiveLaw / Verdictum PDF uploads; CourtListener for US |
| Morgan Stanley / Akamai-gated PDFs | Wayback snapshot |
| CBIC notifications | site is JS-only and challenge-prone → Gazette (egazette) copy of the notification |
| mnre.gov.in (Next.js shell, 2026-10-26) | keyless WordPress API at `https://mnre.gov.in/cms/wp-json/`: `taxonomy/documents_category` (category slugs), `document/documents?document_category=<slug>&limit=50&page=1` (listings; the `type=` form 500s). Files are media IDs the API won't resolve → render the listing page in Obscura and take the `/static/uploads/…pdf` links, which download directly. Press releases only link to PIB (`mincode=28`). Server 504s intermittently. Some uploads are scans (0 text → OCR) |

## How to report what you fetched

For every figure taken from a fetched document, record: URL actually read, document title and date,
page/table/section, and the route (`direct`, `obscura`, `doi-location`, `eu-cellar`, `wayback …`). Mark
`abstract_only` and snippet-only sources as such. Keep the `.log.jsonl` next to the extract; it is the
fetch log reviewers ask for.

## Scheduled (unattended) tasks

Unattended runs hang on any permission prompt, so they call one fixed wrapper that is allowlisted:

```bash
bash /Users/umashankar/bin/fetch_source.sh "<target>" [--name STEM]
```

It always writes to `/Users/Shared/source_fetch/<YYYY-MM-DD>/` (the wrapper refuses `--out`, so the
allowlisted command cannot write anywhere else), then **Read** the `.txt` it reports. Never point `--out` inside a folder that gets committed and pushed (e.g.
`/Users/Shared/lit_review`, whose mirror runs `git add -A`): fetched documents are third-party material. Allow rule (in `~/.claude/settings.json`): `Bash(bash /Users/umashankar/bin/fetch_source.sh *)`.

## Other free tools worth knowing (not in the ladder)

`crawl4ai` (LLM-ready crawling), `lightpanda` (light headless browser), Playwright (scripted browsing),
`pdfplumber`/`camelot` (PDF tables), OpenAlex / Crossref / Unpaywall (scholarly metadata),
Wayback CDX API (`web.archive.org/cdx/search/cdx?url=…`) for snapshot history.
