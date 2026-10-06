#!/usr/bin/env python3
"""Read-only editorial quality scan of every published post (WP + Blogger) -> per-post score + reasons."""
from __future__ import annotations
import collections, html, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_titles_images_v2 import ROOT, get, clean  # noqa: E402
import content_quality_gate as G  # noqa: E402
import audit_openings_v3 as O  # noqa: E402

CLICHE_EN = re.compile(r"in today'?s|in the (?:dynamic|ever[- ]evolving|vibrant|digital) |navigat(?:e|ing) the (?:complex|vast|intricate)|delve|tapestry|rapidly evolving|embark(?:ing)? on|landscape of|ultimate guide|game[- ]changer|unlock(?:ing)? the|seamless(?:ly)?|testament to|it is (?:crucial|essential|important) to|stands as a|beacon of|realm of", re.I)
CLICHE_KO = re.compile(r"오늘날|빠르게 변화하는|점점 더 중요|알아보겠습니다|알아보도록|살펴보겠습니다|도움이 되(?:었|셨)기|결론적으로|핵심은 바로|무엇보다 중요", re.I)
PERSONA = re.compile(r"전문의|의학박사|임상 경력|20년 경력|SEO 전문 블로거|as a (?:doctor|physician|lawyer|attorney)", re.I)


def metrics(title: str, body: str, host: str) -> dict:
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", body or "", flags=re.S | re.I)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()
    cjk = len(re.findall(r"[가-힣ぁ-んァ-ン一-龥]", text))
    words = len(re.findall(r"[A-Za-z0-9']+", text))
    size = words + cjk // 2            # comparable length unit
    h2 = len(re.findall(r"<h2\b", body or "", re.I))
    links = [u for u in re.findall(r'href=["\']([^"\']+)', body or "") if u.startswith("http") and host not in urlparse(u).netloc]
    digits = len(re.findall(r"\d[\d,.%]*", text))
    paras = [p.strip() for p in re.split(r"</p>", body or "") if len(re.sub(r"<[^>]+>", "", p).strip()) > 40]
    ptxt = [re.sub(r"\W+", "", re.sub(r"<[^>]+>", "", p))[:60] for p in paras]
    dup_para = len(ptxt) - len(set(ptxt))
    gate = G.evaluate_article(title, body or "", f"https://{host}")
    reasons, score = [], 100
    if size < 450: score -= 35; reasons.append(f"thin:{size}")
    elif size < 800: score -= 15; reasons.append(f"short:{size}")
    if h2 < 2: score -= 10; reasons.append("few_headings")
    nc = len(CLICHE_EN.findall(text)) + len(CLICHE_KO.findall(text))
    if nc >= 3: score -= min(25, 5 * nc); reasons.append(f"cliche:{nc}")
    if not links: score -= 15; reasons.append("no_external_source")
    if digits < 3: score -= 10; reasons.append("no_concrete_facts")
    if dup_para: score -= 10; reasons.append("dup_paragraph")
    if PERSONA.search(text[:600]): reasons.append("persona_claim")
    if not gate.passed: reasons.append("gate_fail")
    return {"size": size, "h2": h2, "ext_links": len(links), "digits": digits, "cliche": nc, "score": max(0, score), "gate_score": gate.score, "gate_passed": gate.passed, "gate_blockers": gate.blockers[:4], "reasons": reasons,
            "h2_list": [clean(x)[:60] for x in re.findall(r"<h2\b[^>]*>(.*?)</h2>", body or "", flags=re.S | re.I)][:8]}


def main():
    sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    sites = sites if isinstance(sites, list) else sites["sites"]
    out = {}
    for s in sites:
        if s["platform"] != "wordpress" or not s.get("enabled", True):
            continue
        host = urlparse(s["url"]).netloc
        rows, page = [], 1
        while page < 40:
            r = get(f"{s['url']}/wp-json/wp/v2/posts", params={"per_page": 50, "page": page, "status": "publish", "_fields": "id,title,link,date,content"})
            if r.status_code != 200 or not r.json():
                break
            for p in r.json():
                ti = clean(p["title"]["rendered"])
                m = metrics(ti, p["content"]["rendered"], host)
                rows.append({"id": p["id"], "title": ti, "link": p["link"], "date": p["date"][:10], **m})
            if len(r.json()) < 50:
                break
            page += 1
        out[s["site_id"]] = rows
        print(s["site_id"], len(rows), flush=True)
    tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
          "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
    for row in prof["profiles"]:
        bid = row.get("blogspot", {}).get("destination_id")
        if not bid:
            continue
        rows, pt = [], None
        while True:
            p = {"maxResults": 100, "fetchBodies": "true", "status": "LIVE", "fields": "nextPageToken,items(id,title,url,published,content)"}
            if pt: p["pageToken"] = pt
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts", headers=h, params=p, timeout=60); r.raise_for_status()
            d = r.json()
            for x in d.get("items", []):
                host = urlparse(x.get("url", "")).netloc
                m = metrics(clean(x.get("title", "")), x.get("content", ""), host)
                rows.append({"id": x["id"], "blog_id": str(bid), "title": clean(x.get("title", "")), "link": x.get("url", ""), "date": x.get("published", "")[:10], **m})
            pt = d.get("nextPageToken")
            if not pt: break
        out[f"blogger_{row['site_key']}"] = rows
    allp = [dict(r, site=k) for k, v in out.items() for r in v]
    print("posts", len(allp))
    bins = collections.Counter(min(9, r["score"] // 10) * 10 for r in allp)
    print("gate passed:", sum(1 for r in allp if r["gate_passed"]), "of", len(allp))
    print("score bins", sorted(bins.items()))
    rc = collections.Counter(x.split(":")[0] for r in allp for x in r["reasons"])
    print("reasons", rc.most_common())
    for k, v in sorted(out.items()):
        print(f"  {k}: n={len(v)} avg={sum(r['score'] for r in v)/max(1,len(v)):.0f} low(<60)={sum(1 for r in v if r['score']<60)}")
    h2c = collections.Counter(h for r in allp for h in r["h2_list"][:3])
    print("top repeated headings:", [x for x in h2c.most_common(12)])
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/quality_scan_v3.json").write_text(json.dumps({"posts": allp}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
