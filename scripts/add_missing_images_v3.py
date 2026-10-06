#!/usr/bin/env python3
"""Add a free (Pexels/Pixabay) photo to published posts that have no image (WP featured media / Blogger top figure).
Env: APPLY_CHANGES=true to write (default dry run); ONLY_SITES=a,b ; LIMIT_PER_SITE=n.
One photo id is never reused (in-run + photos already on Blogger/WP posts). Newsroom/sensitive-topic posts skipped."""
from __future__ import annotations
import html, json, os, re, sys, time
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_openings_v3 as A  # noqa: E402
from audit_titles_images_v2 import ROOT  # noqa: E402
import blogger_free_image as B  # noqa: E402

APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
ONLY = {x.strip() for x in os.environ.get("ONLY_SITES", "").split(",") if x.strip()}
LIMIT = int(os.environ.get("LIMIT_PER_SITE", "0") or 0)
WP_USER = "huh0303@gmail.com"
UA = {"User-Agent": "Mozilla/5.0 (image-desk)"}
SENSITIVE = re.compile(r"\b(war|strike|attack|killed|death|dead|cancer|patient|diagnos\w*|crime|arrest\w*|murder|suicide|fire|crash)\b|전쟁|공습|사망|숨져|환자|암 |범죄|체포|사고|화재|자살|살인|성폭|학대", re.I)
DEFAULT = {"korea365": "Seoul city skyline", "kstudy": "university campus students", "studyinkorea": "university campus students",
    "oliveyoung": "skincare cosmetics", "kskin": "skincare cosmetics", "jobkorea": "office job interview", "jobinkorea": "office job interview",
    "jobglobal": "business team office", "kvisa": "passport travel documents", "khealth": "healthy lifestyle wellness",
    "ktrip": "Seoul travel street", "kfinance": "finance charts desk", "kinvest": "investment charts laptop",
    "kinsurance": "family home protection", "koreataxlaw": "law books desk", "medicaltour": "modern clinic interior",
    "koreawedding": "wedding flowers table", "kworld": "world map globe", "kcrypto": "cryptocurrency coins", "ktech": "technology circuit board",
    "kieca": "international education students", "ksa": "international students classroom", "sis": "students classroom", "kikorea": "Korea culture street",
    "koreanews": "Seoul city street", "seouljournal": "Seoul city street", "krealestate": "apartment buildings city", "wellness": "yoga wellness",
    "medical_job": "hospital hallway", "life_support": "community helping hands", "kpop": "concert lights stage", "seoul_intl": "school building campus",
    "korea_life": "community helping hands", "medicaltour1": "modern clinic interior"}


def default_query(site: str) -> str:
    key = site.replace("wp_", "").replace("blogger_", "")
    for k, v in DEFAULT.items():
        if k in key:
            return v
    return "Seoul city"


def llm_queries(rows: list[dict]) -> dict[str, str]:
    import economy_text
    out: dict[str, str] = {}
    for i in range(0, len(rows), 15):
        chunk = rows[i:i + 15]
        lines = "\n".join(f"{n}. {r['title']}" for n, r in enumerate(chunk, 1))
        prompt = ("For each blog post title below, write ONE stock-photo search query in English (2-4 words) naming a concrete, "
                  "visually depictable scene or object that fits the topic (no people's names, no brands, no abstract words). "
                  "Return ONLY a JSON array of strings in the same order, one per title.\n" + lines)
        try:
            raw = economy_text.generate_text(prompt, temperature=0.3)
            arr = json.loads(re.search(r"\[.*\]", raw, re.S).group(0))
            for r, q in zip(chunk, arr):
                if isinstance(q, str) and 2 <= len(q) <= 60:
                    out[r["key"]] = q.strip()
        except Exception as e:  # noqa: BLE001
            print("LLM query batch failed:", type(e).__name__, str(e)[:80], flush=True)
    return out


def search(query: str, used: set[str]):
    pk, xk = B._key("PEXELS_API_KEY"), B._key("PIXABAY_KEY") or B._key("PIXABAY_API_KEY")
    if pk:
        try:
            r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": pk},
                             params={"query": query, "orientation": "landscape", "per_page": 20}, timeout=20)
            for p in r.json().get("photos", []) if r.ok else []:
                pid = str(p["id"])
                alt = p.get("alt", "")
                if pid in used or p.get("width", 0) < 1000:
                    continue
                if alt and not B._relevant(query, alt) and not SENSITIVE.search(alt) is None:
                    continue
                if SENSITIVE.search(alt or ""):
                    continue
                return {"id": pid, "url": p["src"]["large"], "author": p.get("photographer", ""), "provider": "Pexels", "page": p.get("url", "")}
        except requests.RequestException:
            pass
    if xk:
        try:
            r = requests.get("https://pixabay.com/api/", params={"key": xk, "q": query, "image_type": "photo", "orientation": "horizontal",
                             "safesearch": "true", "min_width": 1000, "per_page": 20}, timeout=20)
            for p in r.json().get("hits", []) if r.ok else []:
                pid = str(p["id"])
                if pid in used or SENSITIVE.search(p.get("tags", "")):
                    continue
                return {"id": pid, "url": p.get("largeImageURL") or p["webformatURL"], "author": p.get("user", ""), "provider": "Pixabay", "page": p.get("pageURL", "")}
        except requests.RequestException:
            pass
    return None


def used_ids(data) -> set[str]:
    ids = set()
    for rows in data.values():
        for r in rows:
            for u in r.get("urls", []):
                pid = B.photo_id_from_url(u)
                if pid:
                    ids.add(pid)
    try:
        ids |= B.used_photo_ids()
    except Exception:  # noqa: BLE001
        pass
    return ids


def main():
    sites_cfg = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    sites_cfg = sites_cfg if isinstance(sites_cfg, list) else sites_cfg["sites"]
    wp_cfg = {s["site_id"]: s for s in sites_cfg if s["platform"] == "wordpress"}
    data = {}
    for sid, s in wp_cfg.items():
        if ONLY and sid not in ONLY:
            continue
        if s.get("enabled", True):
            data[sid] = A.wp(s["url"])
    try:
        bl = A.blogger()
        data.update({k: v for k, v in bl.items() if not ONLY or k in ONLY})
    except Exception as e:  # noqa: BLE001
        print("BLOGGER FAIL", type(e).__name__, str(e)[:120])
    used = used_ids(data)
    print("posts", sum(len(v) for v in data.values()), "used photo ids", len(used), "apply", APPLY, flush=True)
    token = None
    log = []
    for site, rows in data.items():
        todo = [dict(r, key=f"{site}:{r['id']}") for r in rows if not r["feat"] and not r["imgs"]]
        if LIMIT:
            todo = todo[:LIMIT]
        if not todo:
            continue
        queries = llm_queries(todo)
        print(f"== {site}: {len(todo)} posts without image, llm queries {len(queries)}", flush=True)
        for r in todo:
            rec = {"site": site, "id": r["id"], "title": r["title"][:80]}
            if SENSITIVE.search(r["title"]):
                rec["status"] = "skipped_sensitive_topic"
                log.append(rec); continue
            q = queries.get(r["key"]) or default_query(site)
            pic = search(q, used) or search(default_query(site), used)
            rec["query"] = q
            if not pic:
                rec["status"] = "no_photo_found"
                log.append(rec); continue
            used.add(pic["id"])
            rec.update(photo=f"{pic['provider']}:{pic['id']}", photo_url=pic["page"])
            alt = html.escape(r["title"], quote=True)
            cap = f"Photo: {pic['author']} / {pic['provider']}"
            if not APPLY:
                rec["status"] = "dry_run"; log.append(rec); print("dry", site, r["id"], q, pic["id"], flush=True); continue
            try:
                if site.startswith("blogger_"):
                    if token is None or time.time() - token[1] > 2400:
                        t = requests.post("https://oauth2.googleapis.com/token", data={
                            "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
                            "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
                        token = (t, time.time())
                    h = {"Authorization": f"Bearer {token[0]}"}
                    u = f"https://www.googleapis.com/blogger/v3/blogs/{r['blog_id']}/posts/{r['id']}"
                    cur = requests.get(u, headers=h, timeout=30); cur.raise_for_status()
                    body = cur.json()["content"]
                    if A.imgs_of(body):
                        rec["status"] = "already_has_image"
                    else:
                        fig = (f'<figure style="margin:0 0 1.2em 0;text-align:center"><img src="{pic["url"]}" alt="{alt}" '
                               f'style="max-width:100%;height:auto" loading="lazy"><figcaption style="font-size:.8em;color:#666">{html.escape(cap)}</figcaption></figure>\n')
                        rr = requests.patch(u, headers=h, json={"content": fig + body}, timeout=40)
                        rec["status"] = "updated" if rr.ok else f"failed HTTP {rr.status_code}"
                else:
                    s = wp_cfg[site]
                    auth = (WP_USER, os.environ[s["secret_name"]])
                    img = requests.get(pic["url"], headers=UA, timeout=60); img.raise_for_status()
                    ctype = img.headers.get("content-type", "image/jpeg").split(";")[0]
                    ext = "png" if "png" in ctype else "jpg"
                    mr = requests.post(f"{s['url']}/wp-json/wp/v2/media", auth=auth, data=img.content, timeout=120, headers={
                        "Content-Disposition": f'attachment; filename="{pic["provider"].lower()}-{pic["id"]}.{ext}"', "Content-Type": ctype})
                    mr.raise_for_status()
                    mid = mr.json()["id"]
                    requests.post(f"{s['url']}/wp-json/wp/v2/media/{mid}", auth=auth, json={"alt_text": r["title"][:120], "caption": cap}, timeout=40)
                    pr = requests.post(f"{s['url']}/wp-json/wp/v2/posts/{r['id']}", auth=auth, json={"featured_media": mid}, timeout=40)
                    rec["status"] = "updated" if pr.ok else f"failed HTTP {pr.status_code}"
                    rec["media_id"] = mid
            except Exception as e:  # noqa: BLE001
                rec["status"] = f"error {type(e).__name__}: {str(e)[:100]}"
            log.append(rec)
            print(rec["status"], site, r["id"], q, rec.get("photo"), flush=True)
            time.sleep(0.8)
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/add_images_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    c = {}
    for x in log:
        c[x["status"]] = c.get(x["status"], 0) + 1
    print(json.dumps(c))


if __name__ == "__main__":
    main()
