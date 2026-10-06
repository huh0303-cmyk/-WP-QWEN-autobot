#!/usr/bin/env python3
"""Export weak posts (score < MAX_SCORE, not newsroom/khealth/persona) with their plain text for human/agent research rewrite."""
import html, json, os, re, sys
from pathlib import Path
from urllib.parse import urlparse
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_scan_v3 as Q  # noqa: E402
from audit_titles_images_v2 import ROOT  # noqa: E402
MAX = int(os.environ.get("MAX_SCORE", "70"))
cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8")); cfg = cfg if isinstance(cfg, list) else cfg["sites"]
out = []
def txt(b): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", b or "", flags=re.S)))).strip()
for s in cfg:
    if s["platform"] != "wordpress" or not s.get("enabled", True) or s["site_id"] in ("wp_koreanews", "wp_khealth365"): continue
    host = urlparse(s["url"]).netloc; page = 1
    while page < 40:
        r = Q.get(f"{s['url']}/wp-json/wp/v2/posts", params={"per_page": 50, "page": page, "status": "publish", "_fields": "id,title,link,content"})
        if r.status_code != 200 or not r.json(): break
        for p in r.json():
            ti = Q.clean(p["title"]["rendered"]); m = Q.metrics(ti, p["content"]["rendered"], host)
            if m["score"] < MAX and "persona_claim" not in m["reasons"]:
                out.append({"site": s["site_id"], "id": p["id"], "title": ti, "link": p["link"], "score": m["score"], "reasons": m["reasons"], "text": txt(p["content"]["rendered"])[:2500]})
        if len(r.json()) < 50: break
        page += 1
tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"], "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
for row in prof["profiles"]:
    b = row.get("blogspot", {}).get("destination_id"); site = f"blogger_{row['site_key']}"
    if not b or site in ("blogger_koreanews", "blogger_seouljournal"): continue
    pt = None
    while True:
        pr = {"maxResults": 100, "fetchBodies": "true", "status": "LIVE", "fields": "nextPageToken,items(id,title,url,content)"}
        if pt: pr["pageToken"] = pt
        r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{b}/posts", headers=H, params=pr, timeout=60); r.raise_for_status(); d = r.json()
        for x in d.get("items", []):
            ti = Q.clean(x.get("title", "")); m = Q.metrics(ti, x.get("content", ""), urlparse(x.get("url", "")).netloc)
            if m["score"] < MAX and "persona_claim" not in m["reasons"]:
                out.append({"site": site, "id": x["id"], "blog_id": str(b), "title": ti, "link": x.get("url", ""), "score": m["score"], "reasons": m["reasons"], "text": txt(x.get("content", ""))[:2500]})
        pt = d.get("nextPageToken")
        if not pt: break
out.sort(key=lambda c: c["score"])
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/rewrite_candidates.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print("exported", len(out))
