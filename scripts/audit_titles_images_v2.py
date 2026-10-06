#!/usr/bin/env python3
"""Read-only audit v2 (WP + Blogger): repeated words/phrases in titles and duplicate photos.

Title checks
  - exact duplicate titles (within a site and across the network)
  - a content word (or 2-gram) repeated inside ONE title
  - near-duplicate titles inside a site (same words, reordered / one word changed)
  - signature phrases (3/4-grams) reused by many posts (per site and network wide)
Image checks (content based, not URL based)
  - every featured image + inline <img> is downloaded once and fingerprinted
    (sha256 + dHash/aHash); posts sharing the same photo are grouped, within a site
    and across sites.
Writes artifacts/title_image_audit_v2.json (posts, fingerprints, groups) for the fixers.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
UA = {"User-Agent": "Mozilla/5.0 (title-image-audit)"}
HANGUL = re.compile(r"[가-힣]")
IMG_RE = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"']", re.I)
SKIP_IMG = ("gravatar.com", "s.w.org", "emoji", "/wp-includes/", "favicon", "logo")

STOP = set("""a an the and or but of to in on for with from by at as is are was were be been it its this that these those
you your yours we our us they them their i my me he she his her not no do does did can could should would will may might
how what when where why which who whom whose vs versus about into over under than then there here more most less least
very much many some any all each every other another new best top guide complete ultimate essential everything need know
korea korean south""".split())


def clean(t: str) -> str:
    import html
    return html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()


def words(t: str) -> list[str]:
    t = re.sub(r"\b(\w+)-by-\1\b", r"\1", clean(t).lower())  # step-by-step is one idiom
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).split()


def get(url, **kw):
    last = None
    for i in range(4):
        try:
            return requests.get(url, headers=UA, timeout=kw.pop("timeout", 45), **kw)
        except requests.RequestException as e:  # retry transient network errors
            last = e
            time.sleep(4 * (i + 1))
    raise last


def wp_posts(url: str) -> list[dict]:
    out, page = [], 1
    while page <= 30:
        r = get(f"{url}/wp-json/wp/v2/posts", params={
            "per_page": 50, "page": page, "status": "publish", "_embed": "wp:featuredmedia",
            "_fields": "id,title,date,link,featured_media,content,_embedded"})
        if r.status_code != 200:
            break
        rows = r.json()
        if not rows:
            break
        for p in rows:
            feat = next((m.get("source_url", "") for m in p.get("_embedded", {}).get("wp:featuredmedia", []) if isinstance(m, dict)), "")
            inline = [u for u in IMG_RE.findall(p.get("content", {}).get("rendered", "")) if not any(s in u.lower() for s in SKIP_IMG)]
            out.append({"id": p["id"], "title": clean(p["title"]["rendered"]), "date": p["date"], "link": p["link"],
                        "featured": feat, "inline": inline[:6]})
        if len(rows) < 50:
            break
        page += 1
    return out


def blogger_posts() -> dict[str, list[dict]]:
    tok = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"], "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=25).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    prof = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
    res = {}
    for row in prof["profiles"]:
        bid = row.get("blogspot", {}).get("destination_id")
        if not bid:
            continue
        items, pt = [], None
        while True:
            p = {"maxResults": 500, "fetchBodies": "false", "fetchImages": "true", "status": "LIVE"}
            if pt:
                p["pageToken"] = pt
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts", headers=h, params=p, timeout=40)
            r.raise_for_status()
            d = r.json()
            for x in d.get("items", []):
                imgs = [i["url"] for i in x.get("images", []) if i.get("url")]
                items.append({"id": x["id"], "title": clean(x.get("title", "")), "date": x.get("published", ""),
                              "link": x.get("url", ""), "featured": imgs[0] if imgs else "", "inline": imgs[1:7], "blog_id": str(bid)})
            pt = d.get("nextPageToken")
            if not pt:
                break
        res[f"blogger_{row['site_key']}"] = items
    return res


# ---------------------------------------------------------------- titles
def title_findings(data: dict[str, list[dict]]) -> dict:
    rep_word, rep_bigram, exact_site, exact_net, near = [], [], [], [], []
    net_exact = collections.defaultdict(list)
    gram3, gram4 = collections.defaultdict(set), collections.defaultdict(set)
    open3, end3 = collections.defaultdict(set), collections.defaultdict(set)
    for site, rows in data.items():
        seen = collections.defaultdict(list)
        sets = []
        for r in rows:
            w = words(r["title"])
            norm = " ".join(w)
            seen[norm].append(r)
            net_exact[norm].append((site, r))
            # repeated content word inside one title
            if HANGUL.search(r["title"]):
                cand = [x for x in w if len(x) >= 2]
            else:
                cand = [x for x in w if len(x) >= 4 and x not in STOP and not x.isdigit()]
            c = collections.Counter(cand)
            dup = [k for k, v in c.items() if v >= 2]
            if dup:
                rep_word.append({"site": site, "id": r["id"], "title": r["title"], "words": dup})
            bg = collections.Counter(zip(w, w[1:]))
            bgd = [" ".join(k) for k, v in bg.items() if v >= 2 and not all(x in STOP for x in k)]
            if bgd:
                rep_bigram.append({"site": site, "id": r["id"], "title": r["title"], "bigrams": bgd})
            content = {x for x in w if x not in STOP and len(x) > 2}
            sets.append((r, content))
            key = (site, r["id"])
            for i in range(len(w) - 2):
                g = w[i:i + 3]
                if not all(x in STOP for x in g):
                    gram3[" ".join(g)].add(key)
            for i in range(len(w) - 3):
                gram4[" ".join(w[i:i + 4])].add(key)
            if len(w) >= 3:
                open3[" ".join(w[:3])].add(key)
                end3[" ".join(w[-3:])].add(key)
        for n, rs in seen.items():
            if len(rs) > 1:
                exact_site.append({"site": site, "title": rs[0]["title"], "count": len(rs), "ids": [x["id"] for x in rs]})
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                a, b = sets[i][1], sets[j][1]
                if len(a) >= 4 and len(b) >= 4:
                    jac = len(a & b) / len(a | b)
                    if jac >= 0.8 and " ".join(words(sets[i][0]["title"])) != " ".join(words(sets[j][0]["title"])):
                        near.append({"site": site, "a": sets[i][0]["title"], "b": sets[j][0]["title"], "jaccard": round(jac, 2)})
    for n, lst in net_exact.items():
        if len({s for s, _ in lst}) > 1 or len(lst) > 1:
            if len({s for s, _ in lst}) > 1:
                exact_net.append({"title": lst[0][1]["title"], "sites": sorted({s for s, _ in lst}), "count": len(lst)})

    def top(d, minimum, k=40):
        return [{"phrase": p, "posts": len(v), "sites": len({s for s, _ in v})}
                for p, v in sorted(d.items(), key=lambda kv: -len(kv[1])) if len(v) >= minimum][:k]

    return {"repeated_word_in_title": rep_word, "repeated_bigram_in_title": rep_bigram,
            "exact_dup_within_site": exact_site, "exact_dup_across_sites": exact_net, "near_dup_within_site": near,
            "top_3grams": top(gram3, 8), "top_4grams": top(gram4, 6), "top_openings": top(open3, 6), "top_endings": top(end3, 6)}


# ---------------------------------------------------------------- images
def fp_url(url: str):
    from editorial_image_guard import fingerprint
    if urlparse(url).scheme not in ("http", "https"):
        return None
    try:
        with requests.get(url, headers=UA, timeout=25, stream=True) as r:
            if r.status_code != 200 or not r.headers.get("Content-Type", "").startswith("image/"):
                return {"error": f"HTTP {r.status_code}"}
            data = bytearray()
            for ch in r.iter_content(65536):
                data.extend(ch)
                if len(data) > 12_000_000:
                    return {"error": "oversized"}
        from PIL import Image
        with Image.open(BytesIO(bytes(data))) as im:
            w, h = im.size
        fp = fingerprint(bytes(data))
        return {"sha": fp["sha"], "dhash": fp["dhash"], "ahash": fp["ahash"], "spread": fp["spread"], "w": w, "h": h}
    except Exception as e:  # noqa: BLE001
        return {"error": type(e).__name__}


def image_findings(data: dict[str, list[dict]]) -> dict:
    from editorial_image_guard import same_photo
    urls = sorted({u for rows in data.values() for r in rows for u in ([r["featured"]] if r["featured"] else []) + r["inline"]})
    print(f"fingerprinting {len(urls)} unique image URLs", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=14) as pool:
        fps = dict(zip(urls, pool.map(fp_url, urls)))
    print(f"done in {time.time() - t0:.0f}s; errors={sum(1 for v in fps.values() if v and v.get('error'))}", flush=True)
    refs = []  # (fp, site, post, role, url)
    for site, rows in data.items():
        for r in rows:
            for role, lst in (("featured", [r["featured"]] if r["featured"] else []), ("inline", r["inline"])):
                for u in lst:
                    fp = fps.get(u)
                    if fp and "sha" in fp and min(fp["w"], fp["h"]) >= 300 and fp["spread"] > 5:
                        refs.append((fp, site, r, role, u))
    groups, used = [], set()
    # exact sha first (cheap), then perceptual
    by_sha = collections.defaultdict(list)
    for i, x in enumerate(refs):
        by_sha[x[0]["sha"]].append(i)
    parent = list(range(len(refs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for idxs in by_sha.values():
        for k in idxs[1:]:
            parent[find(k)] = find(idxs[0])
    # perceptual match over unique-sha representatives (all pairs; avoids missed bucket edges)
    reps = sorted({find(i) for i in range(len(refs))})
    for a in range(len(reps)):
        fa = refs[reps[a]][0]
        for b in range(a + 1, len(reps)):
            if find(reps[a]) != find(reps[b]) and same_photo(fa, refs[reps[b]][0]):
                parent[find(reps[b])] = find(reps[a])
    comp = collections.defaultdict(list)
    for i in range(len(refs)):
        comp[find(i)].append(i)
    for idxs in comp.values():
        posts = {(refs[i][1], refs[i][2]["id"]) for i in idxs}
        if len(posts) < 2:
            continue
        groups.append({
            "photo_urls": sorted({refs[i][4] for i in idxs})[:4],
            "sites": sorted({refs[i][1] for i in idxs}),
            "posts": [{"site": refs[i][1], "id": refs[i][2]["id"], "date": refs[i][2]["date"], "role": refs[i][3],
                       "title": refs[i][2]["title"], "link": refs[i][2]["link"], "url": refs[i][4], "blog_id": refs[i][2].get("blog_id", "")} for i in sorted(idxs, key=lambda i: refs[i][2]["date"])],
        })
    groups.sort(key=lambda g: -len(g["posts"]))
    none = {site: sum(1 for r in rows if not r["featured"] and not r["inline"]) for site, rows in data.items()}
    return {"unique_image_urls": len(urls), "fingerprint_errors": sum(1 for v in fps.values() if v and v.get("error")),
            "duplicate_groups": groups, "posts_without_any_image": {k: v for k, v in none.items() if v}}


def main():
    sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    sites = sites if isinstance(sites, list) else sites["sites"]
    data: dict[str, list[dict]] = {}
    for s in sites:
        if s["platform"] == "wordpress" and s.get("enabled", True):
            try:
                data[s["site_id"]] = wp_posts(s["url"])
            except Exception as e:  # noqa: BLE001
                data[s["site_id"]] = []
                print("WP FAIL", s["site_id"], type(e).__name__, str(e)[:100], flush=True)
    try:
        data.update(blogger_posts())
    except Exception as e:  # noqa: BLE001
        print("BLOGGER FAIL", type(e).__name__, str(e)[:160], flush=True)
    total = sum(len(v) for v in data.values())
    print(f"sites={len(data)} posts={total}", flush=True)
    for k, v in sorted(data.items()):
        print(f"  {k}: {len(v)}", flush=True)
    tf = title_findings(data)
    print("\n== TITLES ==")
    for k in ("repeated_word_in_title", "repeated_bigram_in_title", "exact_dup_within_site", "exact_dup_across_sites", "near_dup_within_site"):
        print(f"{k}: {len(tf[k])}")
        for x in tf[k][:12]:
            print("   ", json.dumps(x, ensure_ascii=False)[:230])
    for k in ("top_openings", "top_endings", "top_3grams", "top_4grams"):
        print(f"{k}:")
        for x in tf[k][:15]:
            print("   ", x)
    imf = image_findings(data)
    print("\n== IMAGES ==")
    print("unique urls", imf["unique_image_urls"], "fingerprint errors", imf["fingerprint_errors"], "duplicate groups", len(imf["duplicate_groups"]))
    inpost = sum(len(g["posts"]) for g in imf["duplicate_groups"])
    print("posts involved:", inpost)
    for g in imf["duplicate_groups"][:25]:
        print(f"  x{len(g['posts'])} sites={len(g['sites'])} roles={sorted({p['role'] for p in g['posts']})} {g['photo_urls'][0][:90]}")
        for p in g["posts"][:4]:
            print("       ", p["site"], p["id"], p["title"][:60])
    print("posts without any image:", imf["posts_without_any_image"])
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/title_image_audit_v2.json").write_text(json.dumps(
        {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "posts": data, "titles": tf, "images": imf},
        ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
