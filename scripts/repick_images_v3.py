#!/usr/bin/env python3
"""Re-check photos added on 2026-10-06 (data/add_images_log_2026-10-06.json) against the strict alt-text rule;
replace mismatching ones (WP: new featured media; Blogger: swap figure img/caption). Env: APPLY_CHANGES."""
from __future__ import annotations
import html, json, os, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parent))
import add_missing_images_v3 as M  # noqa: E402
import blogger_free_image as B  # noqa: E402
from audit_titles_images_v2 import ROOT  # noqa: E402

APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
PROVIDER = os.environ.get("PROVIDER", "Pexels")
PX = B._key("PIXABAY_KEY") or B._key("PIXABAY_API_KEY")
log = [x for x in json.load(open(ROOT / "data/add_images_log_2026-10-06.json", encoding="utf-8")) if x.get("status") == "updated"]
extra = ROOT / "data/add_images_log_extra.json"
sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
sites = sites if isinstance(sites, list) else sites["sites"]
wpc = {s["site_id"]: s for s in sites if s["platform"] == "wordpress"}
prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
bid = {f"blogger_{r['site_key']}": r["blogspot"]["destination_id"] for r in prof["profiles"] if r.get("blogspot", {}).get("destination_id")}
pk = B._key("PEXELS_API_KEY")
used = {x["photo"].split(":")[1] for x in log if x.get("photo")}
try:
    used |= B.used_photo_ids()
except Exception:  # noqa: BLE001
    pass
token = None
out, stats = [], {}
for x in log:
    prov, pid = x["photo"].split(":")
    if prov != PROVIDER:
        continue
    if prov == "Pexels":
        r = requests.get(f"https://api.pexels.com/v1/photos/{pid}", headers={"Authorization": pk}, timeout=20)
        alt = r.json().get("alt", "") if r.ok else ""
    else:  # Pixabay: only tags are available
        r = requests.get("https://pixabay.com/api/", params={"key": PX, "id": pid}, timeout=20)
        hits = r.json().get("hits", []) if r.ok else []
        alt = (hits[0].get("tags", "") if hits else "").replace(",", " ")
        time.sleep(0.8)
    if M.alt_ok(alt, x["query"]):
        stats["ok"] = stats.get("ok", 0) + 1
        continue
    pic = M.search(x["query"], used) or M.search(M.default_query(x["site"]), used)
    rec = {"site": x["site"], "id": x["id"], "title": x["title"], "query": x["query"], "old": pid, "old_alt": alt[:80]}
    if not pic:
        rec["status"] = "no_replacement"; out.append(rec); stats["no_replacement"] = stats.get("no_replacement", 0) + 1; continue
    used.add(pic["id"]); rec.update(new=pic["id"], new_alt=pic.get("alt", "")[:80])
    if not APPLY:
        rec["status"] = "dry_run"; out.append(rec); stats["dry_run"] = stats.get("dry_run", 0) + 1; continue
    try:
        cap = f"Photo: {pic['author']} / {pic['provider']}"
        if x["site"].startswith("blogger_"):
            if token is None or time.time() - token[1] > 2400:
                t = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
                    "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
                token = (t, time.time())
            h = {"Authorization": f"Bearer {token[0]}"}
            u = f"https://www.googleapis.com/blogger/v3/blogs/{bid[x['site']]}/posts/{x['id']}"
            body = requests.get(u, headers=h, timeout=30).json()["content"]
            soup = BeautifulSoup(body, "html.parser"); done = False
            for img in soup.find_all("img"):
                fg = img.find_parent("figure")
                if pid in img.get("src", "") or (prov == "Pixabay" and fg and fg.find("figcaption") and "Pixabay" in fg.find("figcaption").get_text()):
                    img["src"] = pic["url"]
                    fig = img.find_parent("figure")
                    cp = fig.find("figcaption") if fig else None
                    if cp:
                        cp.string = cap
                    done = True; break
            if done:
                rr = requests.patch(u, headers=h, json={"content": str(soup)}, timeout=40); rec["status"] = "replaced" if rr.ok else f"failed HTTP {rr.status_code}"
            else:
                rec["status"] = "figure_not_found"
        else:
            s = wpc[x["site"]]; auth = ("huh0303@gmail.com", os.environ[s["secret_name"]])
            img = requests.get(pic["url"], headers=M.UA, timeout=60); img.raise_for_status()
            ctype = img.headers.get("content-type", "image/jpeg").split(";")[0]
            mr = requests.post(f"{s['url']}/wp-json/wp/v2/media", auth=auth, data=img.content, timeout=120, headers={
                "Content-Disposition": f'attachment; filename="{pic["provider"].lower()}-{pic["id"]}.jpg"', "Content-Type": ctype}); mr.raise_for_status()
            mid = mr.json()["id"]
            requests.post(f"{s['url']}/wp-json/wp/v2/media/{mid}", auth=auth, json={"alt_text": x["title"][:120], "caption": cap}, timeout=40)
            pr = requests.post(f"{s['url']}/wp-json/wp/v2/posts/{x['id']}", auth=auth, json={"featured_media": mid}, timeout=40)
            rec["status"] = "replaced" if pr.ok else f"failed HTTP {pr.status_code}"
    except Exception as e:  # noqa: BLE001
        rec["status"] = f"error {type(e).__name__}: {str(e)[:80]}"
    out.append(rec); stats[rec["status"]] = stats.get(rec["status"], 0) + 1
    print(rec["status"], rec["site"], rec["id"], "|", rec["old_alt"][:40], "=>", rec.get("new_alt", "")[:40], flush=True)
    time.sleep(0.7)
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/repick_log.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(stats))
