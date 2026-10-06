#!/usr/bin/env python3
"""Evidence-based rewrite of weak published posts (WP + Blogger).
Flow per post: search the web (DuckDuckGo HTML -> Bing HTML fallback) -> fetch 2-4 authoritative pages -> free-LLM chain writes a
source-grounded article from ONLY that evidence -> deterministic validation -> (optional) replace body, keeping the post's existing photo.
Never publishes a rewrite that fails validation. Env: APPLY_CHANGES, ONLY_SITES, LIMIT, MAX_SCORE (default 70), POST_IDS ('site:id,...').
Previews + backups: artifacts/rewrite_preview/, artifacts/rewrite_backups/."""
from __future__ import annotations
import html, json, os, re, sys, time
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
import requests
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_scan_v3 as Q  # noqa: E402
from audit_titles_images_v2 import ROOT  # noqa: E402

APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
ONLY = {x.strip() for x in os.environ.get("ONLY_SITES", "").split(",") if x.strip()}
LIMIT = int(os.environ.get("LIMIT", "0") or 0)
MAX_SCORE = int(os.environ.get("MAX_SCORE", "70") or 70)
IDS = {x.strip() for x in os.environ.get("POST_IDS", "").split(",") if x.strip()}
TODAY = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.8,ko;q=0.7"}
PREV = Path("artifacts/rewrite_preview"); PREV.mkdir(parents=True, exist_ok=True)
BAK = Path("artifacts/rewrite_backups"); BAK.mkdir(parents=True, exist_ok=True)
GOOD = re.compile(r"\.go\.kr|\.gov\b|\.gov\.|\.or\.kr|\.ac\.kr|\.edu\b|hikorea|visa\.go|nhis|nts\.go|kosis|moj\.go|mofa|kotra|visitkorea|koreaherald|koreatimes|yna\.co\.kr|who\.int|oecd|worldbank|imf\.org|wikipedia\.org|britannica|studyinkorea|unesco|korea\.net", re.I)
BAD = re.compile(r"pinterest|facebook|instagram|youtube\.com|tiktok|quora|reddit|twitter|x\.com|linkedin|amazon|coupang|aliexpress|\.blogspot\.|tistory|naver\.com/blog|blog\.naver|medium\.com", re.I)
CLICHE = Q.CLICHE_EN, Q.CLICHE_KO
HEAD_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def lang(s): return "ko" if len(re.findall(r"[가-힣]", s)) > 20 else ("ja" if len(re.findall(r"[ぁ-んァ-ン]", s)) > 20 else "en")


def ddg(q):
    r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=UA, timeout=25)
    out = []
    for a in BeautifulSoup(r.text, "html.parser").select("a.result__a"):
        h = a.get("href", "")
        if "uddg=" in h:
            h = unquote(parse_qs(urlparse(h).query).get("uddg", [""])[0])
        if h.startswith("http"):
            out.append((a.get_text(" ", strip=True), h))
    return out


def _bing_url(h):
    import base64
    if "bing.com/ck/a" in h:
        u = parse_qs(urlparse(h).query).get("u", [""])[0]
        if u.startswith("a1"):
            u = u[2:]; u += "=" * (-len(u) % 4)
            try:
                return base64.urlsafe_b64decode(u).decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                return ""
        return ""
    return h


def bing(q):
    r = requests.get("https://www.bing.com/search", params={"q": q, "setlang": "en"}, headers=UA, timeout=25)
    out = []
    for a in BeautifulSoup(r.text, "html.parser").select("li.b_algo h2 a"):
        u = _bing_url(a.get("href", ""))
        if u.startswith("http"):
            out.append((a.get_text(" ", strip=True), u))
    return out


def wiki(q):
    r = requests.get("https://en.wikipedia.org/w/api.php", params={"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 3}, headers=UA, timeout=25)
    return [(x["title"], "https://en.wikipedia.org/wiki/" + x["title"].replace(" ", "_")) for x in r.json().get("query", {}).get("search", [])]


def search(q):
    for fn in (bing, ddg):
        try:
            res = fn(q)
            if res:
                return res
        except Exception as e:  # noqa: BLE001
            print("   search", fn.__name__, type(e).__name__, flush=True)
        time.sleep(2)
    return []


def page_text(url):
    r = requests.get(url, headers=UA, timeout=25)
    if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
        return None
    s = BeautifulSoup(r.text, "html.parser")
    for t in s(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        t.decompose()
    title = (s.title.get_text(" ", strip=True) if s.title else urlparse(url).netloc)[:120]
    paras = [p.get_text(" ", strip=True) for p in s.find_all(["p", "li"])]
    text = " ".join(p for p in paras if len(p) > 50)[:3500]
    return (title, text) if len(text) > 600 else None


def gather(title, host):
    base = HEAD_YEAR.sub("", title)
    qs = [f"{base} official guide", base]
    seen, ev = set(), []
    cands = []
    for q in qs:
        cands += search(q)
        if len(cands) >= 8:
            break
    try:
        cands += wiki(base)[:2]
    except Exception:  # noqa: BLE001
        pass
    cands.sort(key=lambda x: (0 if GOOD.search(x[1]) else 1))
    for ttl, url in cands:
        d = urlparse(url).netloc
        if d in seen or BAD.search(url) or host in d:
            continue
        try:
            pt = page_text(url)
        except Exception:  # noqa: BLE001
            pt = None
        if pt:
            seen.add(d); ev.append({"title": pt[0], "url": url, "text": pt[1]})
        if len(ev) >= 4:
            break
        time.sleep(1)
    return ev


def build_prompt(title, language, ev, old_text, feedback=""):
    lang_name = {"ko": "Korean", "ja": "Japanese", "en": "English"}[language]
    blocks = "\n\n".join(f"[SOURCE {i+1}] {e['title']} ({e['url']})\n{e['text']}" for i, e in enumerate(ev))
    return (f"Write a helpful, original, reader-first {lang_name} article titled: {title}\n"
            f"Audience: people planning/living/studying/working in Korea. It will be judged for Google AdSense quality (E-E-A-T, original value, no filler).\n"
            f"HARD RULES:\n- Use ONLY facts found in the SOURCE blocks below (and generic common-sense framing). Do NOT invent statistics, fees, dates, rules, names or quotes. If sources do not state a number, do not give one.\n"
            f"- Attribute facts in the text, e.g. 'According to <source name>, ...' using the real source names. Never claim personal experience or professional credentials.\n"
            f"- Answer the main reader question in the first 2-3 sentences. Do NOT open with a cliche ('In today's', 'Navigating', 'Embarking', 오늘날, 알아보겠습니다...).\n"
            f"- 900-1300 words (Korean: about 2200-3200 characters). 5-6 <h2> sections with specific headings (not generic), short paragraphs, a bulleted checklist or step list where useful, and one short 'Common mistakes' or 'What to verify' section.\n"
            f"- Last section: a brief note that rules change and the reader should confirm with the official body (name it if the sources do), then <h2>Sources</h2> with a <ul> of <a href=URL>source title</a> for the sources you actually used (at least 2).\n"
            f"- Output ONLY clean HTML using <h2>,<p>,<ul>,<ol>,<li>,<strong>,<a>,<table>. No markdown, no code fences, no <h1>, no images.\n"
            + (f"- Previous attempt was rejected because: {feedback}. Fix that.\n" if feedback else "")
            + f"\nEXISTING THIN VERSION (for topic scope only; do not copy its claims unless a SOURCE supports them):\n{old_text[:1200]}\n\n{blocks}\n")


def validate(body, ev, old_text, language, title):
    errs = []
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
    cjk = len(re.findall(r"[가-힣ぁ-んァ-ン一-龥]", t)); words = len(re.findall(r"[A-Za-z0-9']+", t))
    size = words + cjk // 2
    if size < 750: errs.append(f"too short ({size})")
    if len(re.findall(r"<h2\b", body, re.I)) < 4: errs.append("fewer than 4 h2")
    urls = {e["url"] for e in ev}
    links = set(re.findall(r'href=["\']([^"\']+)', body))
    if len(links & urls) < 2: errs.append("fewer than 2 real source links")
    if links - urls: errs.append("link not from sources")
    if sum(len(c.findall(t)) for c in CLICHE) >= 2: errs.append("cliche phrases")
    if re.search(r"```|<h1|<img|as an ai|language model", body, re.I): errs.append("forbidden markup/leak")
    if re.search(r"I (?:personally|tested|visited)|my (?:clinic|patient|experience)|제가 직접|제 경험", t, re.I): errs.append("first-person experience claim")
    allowed = set(re.findall(r"\d[\d,.]*", " ".join(e["text"] for e in ev) + " " + old_text + " " + title))
    bad = [n for n in re.findall(r"\d[\d,.]*", t) if n.rstrip(".,") not in {a.rstrip(".,") for a in allowed} and not (len(n.rstrip(".,")) <= 1 or n.rstrip(".,") in {"10", "12", "2026", "24", "30", "1", "2", "3", "4", "5", "6", "7"})]
    if len(bad) > 2: errs.append(f"numbers not in sources: {bad[:5]}")
    if lang(t) != language and not (language == "en" and lang(t) == "en"): errs.append("wrong language")
    return errs, size


def clean_html(raw):
    raw = re.sub(r"^```(?:html)?|```$", "", raw.strip(), flags=re.M).strip()
    m = re.search(r"<h2|<p", raw)
    return raw[m.start():] if m else raw


def first_figure(body):
    s = BeautifulSoup(body or "", "html.parser")
    img = s.find("img")
    if not img:
        return ""
    return str(img.find_parent("figure") or img)


def main():
    import economy_text
    cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    cfg = cfg if isinstance(cfg, list) else cfg["sites"]
    wpc = {s["site_id"]: s for s in cfg if s["platform"] == "wordpress"}
    prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
    bid = {f"blogger_{r['site_key']}": r["blogspot"]["destination_id"] for r in prof["profiles"] if r.get("blogspot", {}).get("destination_id")}
    # --- candidate list from live scan (reuses scan code)
    cands = []
    for site, s in wpc.items():
        if not s.get("enabled", True) or (ONLY and site not in ONLY) or site in ("wp_koreanews", "wp_khealth365"):
            continue
        host = urlparse(s["url"]).netloc; page = 1
        while page < 40:
            r = Q.get(f"{s['url']}/wp-json/wp/v2/posts", params={"per_page": 50, "page": page, "status": "publish", "_fields": "id,title,link,content"})
            if r.status_code != 200 or not r.json(): break
            for p in r.json():
                ti = Q.clean(p["title"]["rendered"]); m = Q.metrics(ti, p["content"]["rendered"], host)
                if m["score"] < MAX_SCORE and "persona_claim" not in m["reasons"]:
                    cands.append({"site": site, "id": p["id"], "title": ti, "host": host, "score": m["score"], "reasons": m["reasons"]})
            if len(r.json()) < 50: break
            page += 1
    tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
          "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    for site, b in bid.items():
        if (ONLY and site not in ONLY) or site in ("blogger_koreanews", "blogger_seouljournal"):
            continue
        pt = None
        while True:
            pr = {"maxResults": 100, "fetchBodies": "true", "status": "LIVE", "fields": "nextPageToken,items(id,title,url,content)"}
            if pt: pr["pageToken"] = pt
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{b}/posts", headers=H, params=pr, timeout=60); r.raise_for_status(); d = r.json()
            for x in d.get("items", []):
                host = urlparse(x.get("url", "")).netloc; ti = Q.clean(x.get("title", "")); m = Q.metrics(ti, x.get("content", ""), host)
                if m["score"] < MAX_SCORE and "persona_claim" not in m["reasons"]:
                    cands.append({"site": site, "id": x["id"], "title": ti, "host": host, "score": m["score"], "reasons": m["reasons"], "blog_id": str(b)})
            pt = d.get("nextPageToken")
            if not pt: break
    if IDS:
        cands = [c for c in cands if f"{c['site']}:{c['id']}" in IDS]
    cands.sort(key=lambda c: c["score"])
    if LIMIT: cands = cands[:LIMIT]
    print("candidates", len(cands), "apply", APPLY, flush=True)
    log = []
    for c in cands:
        rec = {"site": c["site"], "id": c["id"], "title": c["title"][:80], "score_before": c["score"]}
        try:
            # current body
            if c["site"].startswith("blogger_"):
                u = f"https://www.googleapis.com/blogger/v3/blogs/{c['blog_id']}/posts/{c['id']}"
                body = requests.get(u, headers=H, timeout=30).json()["content"]
            else:
                s = wpc[c["site"]]; auth = ("huh0303@gmail.com", os.environ[s["secret_name"]])
                body = requests.get(f"{s['url']}/wp-json/wp/v2/posts/{c['id']}", auth=auth, params={"context": "edit"}, timeout=30).json()["content"]["raw"]
            old_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
            language = lang(old_text + c["title"])
            ev = gather(c["title"], c["host"])
            rec["sources"] = [e["url"] for e in ev]
            if len(ev) < 2:
                rec["status"] = "no_evidence"; log.append(rec); print("no_evidence", c["site"], c["id"], flush=True); continue
            new, feedback, errs, size = None, "", ["not tried"], 0
            for attempt in range(3):
                raw = economy_text.generate_text(build_prompt(c["title"], language, ev, old_text, feedback), temperature=0.4)
                cand_html = clean_html(raw)
                errs, size = validate(cand_html, ev, old_text, language, c["title"])
                if not errs:
                    new = cand_html; break
                feedback = "; ".join(errs); time.sleep(3)
            rec["errors"] = errs
            (PREV / f"{c['site']}-{c['id']}.html").write_text(cand_html if raw else "", encoding="utf-8")
            if not new:
                rec["status"] = "validation_failed"; log.append(rec); print("validation_failed", c["site"], c["id"], errs, flush=True); continue
            final = first_figure(body) + "\n" + new
            rec["size"] = size
            if not APPLY:
                rec["status"] = "dry_run_ok"; log.append(rec); print("dry_run_ok", c["site"], c["id"], size, len(ev), flush=True); continue
            (BAK / f"{c['site']}-{c['id']}.html").write_text(body, encoding="utf-8")
            if c["site"].startswith("blogger_"):
                rr = requests.patch(u, headers=H, json={"content": final}, timeout=60)
            else:
                rr = requests.post(f"{s['url']}/wp-json/wp/v2/posts/{c['id']}", auth=auth, json={"content": final}, timeout=60)
            rec["status"] = "rewritten" if rr.ok else f"failed HTTP {rr.status_code}"
            print(rec["status"], c["site"], c["id"], size, flush=True)
        except Exception as e:  # noqa: BLE001
            rec["status"] = f"error {type(e).__name__}: {str(e)[:100]}"; print(rec["status"], c["site"], c["id"], flush=True)
        log.append(rec); time.sleep(4)
    Path("artifacts/rewrite_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    cnt = {}
    for x in log: cnt[x["status"]] = cnt.get(x["status"], 0) + 1
    print(json.dumps(cnt))


if __name__ == "__main__":
    main()
