#!/usr/bin/env python3
"""Set off-topic (WordPress-theme promo) posts to private on WP sites. Reversible (status=private, nothing deleted).
Env: APPLY_CHANGES=true to write; ONLY_SITES. Flags posts whose title or first 600 chars match THEME. Backups -> artifacts/offtopic_backups/."""
import json, os, re, sys, time
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_titles_images_v2 import ROOT, get  # noqa: E402

APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
ONLY = {x.strip() for x in os.environ.get("ONLY_SITES", "").split(",") if x.strip()}
THEME = re.compile(r"AF Themes|Dynamic World of WordPress|WordPress (theme|themes)|워드프레스 테마|Elementor|Astra theme|Themeforest", re.I)
OUT = Path("artifacts/offtopic_backups"); OUT.mkdir(parents=True, exist_ok=True)
sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
sites = sites if isinstance(sites, list) else sites["sites"]
log = []
for s in sites:
    if s["platform"] != "wordpress" or not s.get("enabled", True) or (ONLY and s["site_id"] not in ONLY):
        continue
    auth = ("huh0303@gmail.com", os.environ[s["secret_name"]])
    page = 1
    while page < 40:
        r = get(f"{s['url']}/wp-json/wp/v2/posts", params={"per_page": 50, "page": page, "status": "publish", "_fields": "id,title,link,content"})
        if r.status_code != 200 or not r.json():
            break
        for p in r.json():
            t = re.sub(r"<[^>]+>", " ", p["title"]["rendered"])
            c = re.sub(r"<[^>]+>", " ", p["content"]["rendered"])[:600]
            if THEME.search(t) or THEME.search(c):
                rec = {"site": s["site_id"], "id": p["id"], "title": t[:90], "link": p["link"]}
                if APPLY:
                    (OUT / f"{s['site_id']}-{p['id']}.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
                    u = requests.post(f"{s['url']}/wp-json/wp/v2/posts/{p['id']}", auth=auth, json={"status": "private"}, timeout=40)
                    rec["status"] = "private" if u.ok else f"failed HTTP {u.status_code}"
                    time.sleep(0.5)
                else:
                    rec["status"] = "dry_run"
                log.append(rec); print(rec["status"], rec["site"], rec["id"], rec["title"], flush=True)
        if len(r.json()) < 50:
            break
        page += 1
Path("artifacts/offtopic_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
print("TOTAL", len(log))
