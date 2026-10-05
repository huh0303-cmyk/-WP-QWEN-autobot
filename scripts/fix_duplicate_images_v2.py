#!/usr/bin/env python3
"""Remove reused photos (content-fingerprint duplicates) from newer posts on WP + Blogger.

Keeps the OLDEST post's copy of every photo; strips the <img> (and its <figure>) from later posts,
matching the existing repair policy (repair_wp_duplicate_images.py). Titles/slugs/text untouched.
Env: APPLY_CHANGES=true to write (default dry-run). Backups -> artifacts/dup_image_backups/.
"""
from __future__ import annotations
import html, json, os, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_titles_images_v2 as A  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
WP_USER = "huh0303@gmail.com"
OUT = Path("artifacts/dup_image_backups")
OUT.mkdir(parents=True, exist_ok=True)


def base(u: str) -> str:
    return re.sub(r"[?#].*$", "", html.unescape(u or "")).rsplit("/", 1)[-1].lower()


def strip_imgs(body: str, urls: set[str]) -> tuple[str, int]:
    names = {base(u) for u in urls}
    soup = BeautifulSoup(body, "html.parser")
    n = 0
    for img in list(soup.find_all("img")):
        if base(img.get("src", "")) in names:
            holder = img.find_parent("figure") or (img.find_parent("a") if img.find_parent("a") and not img.find_parent("a").get_text(strip=True) else None)
            (holder or img).decompose()
            n += 1
    return str(soup), n


def main():
    cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    cfg = cfg if isinstance(cfg, list) else cfg["sites"]
    wp = {s["site_id"]: s for s in cfg if s["platform"] == "wordpress" and s.get("enabled", True)}
    data = {sid: A.wp_posts(s["url"]) for sid, s in wp.items()}
    data.update(A.blogger_posts())
    groups = A.image_findings(data)["duplicate_groups"]
    print(f"duplicate groups={len(groups)} apply={APPLY}", flush=True)
    todo: dict[tuple, set] = {}
    meta: dict[tuple, dict] = {}
    for g in groups:
        for p in g["posts"][1:]:  # posts are date-sorted; keep oldest
            todo.setdefault((p["site"], str(p["id"])), set()).add(p["url"])
            meta[(p["site"], str(p["id"]))] = p
    token = None
    log = []
    for (site, pid), urls in todo.items():
        rec = {"site": site, "id": pid, "title": meta[(site, pid)]["title"], "removed_urls": sorted(urls)}
        try:
            if site.startswith("blogger_"):
                if token is None:
                    token = requests.post("https://oauth2.googleapis.com/token", data={
                        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
                        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
                bid = meta[(site, pid)]["blog_id"]
                h = {"Authorization": f"Bearer {token}"}
                cur = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts/{pid}", headers=h, timeout=30)
                cur.raise_for_status()
                body = cur.json()["content"]
                new, n = strip_imgs(body, urls)
                rec["imgs_removed"] = n
                if n and APPLY:
                    (OUT / f"{site}-{pid}.html").write_text(body, encoding="utf-8")
                    r = requests.patch(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts/{pid}", headers=h, json={"content": new}, timeout=40)
                    rec["status"] = "updated" if r.ok else f"failed HTTP {r.status_code}"
                else:
                    rec["status"] = "dry_run" if n else "no_img_in_body"
            else:
                s = wp[site]
                auth = (WP_USER, os.environ[s["secret_name"]])
                target = f"{s['url']}/wp-json/wp/v2/posts/{pid}"
                cur = requests.get(target, auth=auth, params={"context": "edit"}, timeout=30)
                cur.raise_for_status()
                body = cur.json()["content"]["raw"]
                new, n = strip_imgs(body, urls)
                rec["imgs_removed"] = n
                if n and APPLY:
                    (OUT / f"{site}-{pid}.html").write_text(body, encoding="utf-8")
                    r = requests.post(target, auth=auth, json={"content": new}, timeout=40)
                    rec["status"] = "updated" if r.ok else f"failed HTTP {r.status_code}"
                else:
                    rec["status"] = "dry_run" if n else "no_img_in_body"
        except Exception as e:  # noqa: BLE001
            rec["status"] = f"error {type(e).__name__}: {str(e)[:100]}"
        log.append(rec)
        print(rec["status"], site, pid, rec.get("imgs_removed"), rec["title"][:50], flush=True)
        time.sleep(0.6)
    Path("artifacts/dup_image_fix_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"groups": len(groups), "posts": len(log), "updated": sum(1 for x in log if x["status"] == "updated")}))


if __name__ == "__main__":
    main()
