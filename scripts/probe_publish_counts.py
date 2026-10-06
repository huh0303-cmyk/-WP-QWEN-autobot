"""Read-only: public posts per site per KST day (last 4 days), WP + Blogger + koreanews."""
from __future__ import annotations
import json, os, time
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0"}
now = time.time() + 9 * 3600
days = [time.strftime("%m-%d", time.gmtime(now - 86400 * i)) for i in range(4)]
after = time.strftime("%Y-%m-%dT00:00:00", time.gmtime(now - 86400 * 3))
out = {}
cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8")); cfg = cfg if isinstance(cfg, list) else cfg["sites"]
for s in cfg:
    if s["platform"] != "wordpress" or not s.get("enabled", True): continue
    c = {d: 0 for d in days}; err = ""
    try:
        r = requests.get(f"{s['url']}/wp-json/wp/v2/posts", params={"per_page": 100, "after": after, "_fields": "date"}, headers=UA, timeout=30)
        if r.status_code == 200:
            for p in r.json():
                d = p["date"][5:10]
                if d in c: c[d] += 1
        else: err = f"HTTP {r.status_code}"
    except Exception as e: err = type(e).__name__
    out[s["site_id"]] = {"counts": c, "err": err}
tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
      "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
for row in prof["profiles"]:
    bid = row.get("blogspot", {}).get("destination_id")
    if not bid: continue
    c = {d: 0 for d in days}; err = ""
    try:
        r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts", headers=H, params={"maxResults": 50, "status": "LIVE", "orderBy": "published", "fields": "items(published)"}, timeout=40)
        if r.ok:
            for p in r.json().get("items", []):
                # published is RFC3339 with +09:00 offset typically
                d = p["published"][5:10]
                if d in c: c[d] += 1
        else: err = f"HTTP {r.status_code}"
    except Exception as e: err = type(e).__name__
    out[f"blogger_{row['site_key']}"] = {"counts": c, "err": err}
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/publish_counts.json").write_text(json.dumps({"days": days, "sites": out}, ensure_ascii=False, indent=1))
for plat in ("wp_", "blogger_"):
    ss = {k: v for k, v in out.items() if k.startswith(plat)}
    print(plat, "sites", len(ss), {d: sum(1 for v in ss.values() if v["counts"][d] > 0) for d in days}, "errs", sum(1 for v in ss.values() if v["err"]))
