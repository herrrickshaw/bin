#!/usr/bin/env python3
"""fetch_source — get a primary document (web page, PDF, paper, EU act) as text.

Fallback ladder, stopping at the first route that yields real content:
  1. direct GET with a browser User-Agent        (HTML -> text, PDF -> pdftotext)
  2. Obscura headless browser                    (only when the page needs JavaScript to render)
  3. official alternates for identifiers:
       doi:<doi>     OpenAlex locations (publisher OA, institutional repositories), Crossref metadata
       celex:<id>    EU Publications Office (CELLAR) — use instead of EUR-Lex
       arxiv:<id>    arxiv.org abs + pdf
  4. Wayback Machine snapshot

Hard rule: a bot challenge (CAPTCHA, "verify you're not a robot", Cloudflare/Akamai/AWS-WAF, login
wall) is recorded as BLOCKED and that host is not retried. The tool never impersonates browser TLS
fingerprints, rotates identities or solves challenges. It only looks for the same document elsewhere.

Usage:
  fetch_source.py <url | doi:10.x/y | celex:32023R0956 | arxiv:2605.19337> [--out DIR] [--name STEM]
                  [--insecure] [--no-browser] [--quiet]
Prints one JSON summary on stdout; writes <stem>.<ext>, <stem>.txt and <stem>.log.jsonl into --out.
Exit codes: 0 = got content, 2 = blocked/unavailable everywhere, 1 = bad arguments.
"""
import argparse, gzip, html, http.cookiejar, json, os, re, shutil, ssl, subprocess, sys, time, urllib.parse, urllib.request, zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/143.0 Safari/537.36")
OBSCURA = os.path.expanduser("~/.local/share/obscura/obscura")
CHALLENGE = re.compile(r"(?is)just a moment\.\.\.|challenge-platform|cf-chl-|client challenge|"
                       r"verify (?:that )?you(?:'| a)re (?:not a robot|human)|are you a robot|captcha|"
                       r"access denied.{0,80}akamai|_incapsula_|perimeterx|"
                       r"javascript is disabled.{0,200}robot")
MIN_TEXT = 400          # fewer extracted characters than this = "no real content"
_last_hit = {}          # host -> time of last request (politeness: >=1 s per host)


def log(state, **kw):
    kw["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state["log"].append(kw)
    if not state["quiet"]:
        print(f"[fetch_source] {kw.get('route')}: {kw.get('result')} {kw.get('url', '')}", file=sys.stderr)


def polite(url):
    host = urllib.parse.urlsplit(url).netloc
    wait = 1.0 - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def http_get(url, state, accept=None, timeout=40):
    polite(url)
    hdr = {"User-Agent": UA, "Accept-Language": "en;q=0.9"}
    if accept:
        hdr["Accept"] = accept
    if "opener" not in state:  # one cookie jar per run, as a browser keeps (Springer redirects without it)
        ctx = ssl._create_unverified_context() if state["insecure"] else ssl.create_default_context()
        state["opener"] = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request(url, headers=hdr)
    try:
        with state["opener"].open(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type", ""), decode(r.read(), r.headers), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), decode(e.read() or b"", e.headers), url
    except Exception as e:  # DNS, TLS, timeout
        return 0, "", str(e).encode(), url


def decode(raw, headers):
    """Undo gzip/deflate (Wayback id_ snapshots replay the original Content-Encoding)."""
    enc = (headers.get("Content-Encoding") or "").lower()
    try:
        if raw[:2] == b"\x1f\x8b" or "gzip" in enc:
            return gzip.decompress(raw)
        if "deflate" in enc:
            return zlib.decompress(raw)
    except Exception:
        pass
    return raw


def html_to_text(raw):
    s = raw.decode("utf-8", "ignore")
    s = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|table)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", s)).strip()


def pdf_to_text(path):
    if not shutil.which("pdftotext"):
        return ""
    r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
    return r.stdout.strip()


def save(state, raw, ctype, text, route, url):
    ext = "pdf" if ("pdf" in ctype or raw[:5] == b"%PDF-") else "html"
    stem = os.path.join(state["out"], state["name"])
    with open(f"{stem}.{ext}", "wb") as f:
        f.write(raw)
    if ext == "pdf":
        text = pdf_to_text(f"{stem}.pdf")
    with open(f"{stem}.txt", "w") as f:
        f.write(text)
    state["result"] = {"ok": True, "route": route, "url": url, "file": f"{stem}.{ext}",
                       "text_file": f"{stem}.txt", "chars": len(text)}
    return True


def try_url(url, state, route="direct", accept=None, allow_browser=True):
    host = urllib.parse.urlsplit(url).netloc
    if host in state["blocked_hosts"]:
        log(state, route=route, url=url, result="skipped (host blocked earlier)")
        return False
    code, ctype, raw, final = http_get(url, state, accept)
    head = raw[:200000].decode("utf-8", "ignore")
    if CHALLENGE.search(head) or code in (401, 403, 429) and "pdf" not in ctype:
        state["blocked_hosts"].add(host)
        log(state, route=route, url=url, status=code, result="BLOCKED (bot challenge / denied) — not retried")
        return False
    if code != 200 or not raw:
        log(state, route=route, url=url, status=code, result="no content")
        return False
    if "pdf" in ctype or raw[:5] == b"%PDF-":
        log(state, route=route, url=final, status=code, result="pdf")
        return save(state, raw, "application/pdf", "", route, final)
    text = html_to_text(raw)
    if len(text) >= MIN_TEXT:
        log(state, route=route, url=final, status=code, result=f"html ({len(text)} chars)")
        return save(state, raw, ctype, text, route, final)
    log(state, route=route, url=final, status=code, result=f"thin page ({len(text)} chars) — likely JS-rendered")
    if allow_browser and state["browser"] and os.path.exists(OBSCURA):
        polite(url)
        r = subprocess.run([OBSCURA, "fetch", url, "--dump", "text", "--timeout", "40"],
                           capture_output=True, text=True, timeout=90)
        t = r.stdout.strip()
        if CHALLENGE.search(t[:20000]):
            state["blocked_hosts"].add(host)
            log(state, route="obscura", url=url, result="BLOCKED (bot challenge) — not retried")
        elif len(t) >= MIN_TEXT:
            log(state, route="obscura", url=url, result=f"rendered ({len(t)} chars)")
            return save(state, t.encode(), "text/html", t, "obscura", url)
        else:
            log(state, route="obscura", url=url, result="still thin")
    return False


def wayback(url, state):
    code, _, raw, _ = http_get("https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe=""), state)
    try:
        snap = json.loads(raw)["archived_snapshots"]["closest"]
    except Exception:
        snap = None
    if not snap or not snap.get("available"):
        log(state, route="wayback", url=url, result="no snapshot")
        return False
    # id_ = original bytes without the Wayback toolbar
    raw_url = re.sub(r"/web/(\d+)/", r"/web/\1id_/", snap["url"])
    return try_url(raw_url, state, route=f"wayback {snap.get('timestamp', '')}", allow_browser=False)


def via_doi(doi, state):
    code, _, raw, _ = http_get(f"https://api.openalex.org/works/doi:{doi}", state)
    cands, meta = [], {}
    if code == 200:
        d = json.loads(raw)
        meta = {"title": d.get("title"), "year": d.get("publication_year"), "openalex": d.get("id")}
        for loc in [d.get("best_oa_location") or {}] + d.get("locations", []):
            for k in ("pdf_url", "landing_page_url"):
                if loc.get(k) and loc[k] not in cands:
                    cands.append(loc[k])
        log(state, route="openalex", url=doi, result=f"{len(cands)} locations")
    else:
        log(state, route="openalex", url=doi, status=code, result="not found")
    code, _, raw, _ = http_get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", state)
    if code == 200:
        m = json.loads(raw)["message"]
        meta.setdefault("title", (m.get("title") or [""])[0])
        if m.get("abstract"):
            meta["abstract"] = re.sub(r"<[^>]+>", "", m["abstract"])
    state["meta"] = meta
    # repositories first (least likely to challenge), publisher last
    cands.sort(key=lambda u: ("doi.org" in u, "springer" in u or "elsevier" in u or "wiley" in u))
    for u in cands + [f"https://doi.org/{doi}"]:
        if try_url(u, state, route="doi-location"):
            return True
    if meta.get("abstract"):
        t = f"{meta.get('title', '')}\n\nABSTRACT ONLY (Crossref):\n{meta['abstract']}"
        log(state, route="crossref", url=doi, result="abstract only")
        save(state, t.encode(), "text/plain", t, "crossref-abstract", f"https://doi.org/{doi}")
        state["result"]["abstract_only"] = True
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--out", default="./sources")
    ap.add_argument("--name")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (some .gov.in hosts)")
    ap.add_argument("--no-browser", action="store_true", help="never use Obscura")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tgt = a.target.strip()
    # always sanitised (also a user-supplied --name), so output can never escape --out
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", a.name or re.sub(r"^https?://", "", tgt))[:80].strip("_.") or "source"
    state = {"log": [], "blocked_hosts": set(), "out": a.out, "name": name, "insecure": a.insecure,
             "browser": not a.no_browser, "quiet": a.quiet, "result": None, "meta": {}}

    ok = False
    if tgt.lower().startswith("doi:") or re.match(r"^10\.\d{4,}/", tgt):
        ok = via_doi(re.sub(r"(?i)^doi:", "", tgt), state)
    elif tgt.lower().startswith("celex:"):
        celex = tgt.split(":", 1)[1]
        ok = try_url(f"http://publications.europa.eu/resource/celex/{celex}", state, route="eu-cellar",
                     accept="application/xhtml+xml, text/html;q=0.9, application/pdf;q=0.5")
    elif tgt.lower().startswith("arxiv:"):
        aid = tgt.split(":", 1)[1]
        ok = try_url(f"https://arxiv.org/pdf/{aid}", state, route="arxiv") or \
             try_url(f"https://arxiv.org/abs/{aid}", state, route="arxiv")
    else:
        ok = try_url(tgt, state)
        m = re.search(r"(?:doi\.org/|/doi/(?:abs/|full/|pdf/)?)(10\.\d{4,}/[^\s?#]+)", tgt)
        if not ok and m:
            ok = via_doi(m.group(1), state)
        if not ok and "eur-lex.europa.eu" in tgt:
            c = re.search(r"CELEX(?::|%3A)([0-9][0-9A-Z()]+)", tgt, re.I)
            if c:
                ok = try_url(f"http://publications.europa.eu/resource/celex/{c.group(1)}", state, route="eu-cellar",
                             accept="application/xhtml+xml, text/html;q=0.9")
        if not ok:
            ok = wayback(tgt, state)

    with open(os.path.join(a.out, f"{name}.log.jsonl"), "w") as f:
        for row in state["log"]:
            f.write(json.dumps(row) + "\n")
    out = state["result"] or {"ok": False, "route": None,
                              "reason": "unavailable on every route" + (" (bot-blocked: " + ", ".join(sorted(state["blocked_hosts"])) + ")" if state["blocked_hosts"] else "")}
    out.update({"target": tgt, "blocked_hosts": sorted(state["blocked_hosts"]), "meta": state["meta"],
                "log_file": os.path.join(a.out, f"{name}.log.jsonl")})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out["ok"] else 2)


if __name__ == "__main__":
    main()
