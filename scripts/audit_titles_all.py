#!/usr/bin/env python3
"""Read-only: collect titles from all enabled WP sites (public REST) + Blogger (API), report duplicates/repeated patterns."""
from __future__ import annotations
import json, os, re, collections
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (title-audit)"}


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()


def wp_titles(url):
    out, page = [], 1
    while page <= 20:
        r = requests.get(f"{url}/wp-json/wp/v2/posts", params={"per_page": 100, "page": page, "_fields": "id,title,date,status,link"},
                         headers=UA, timeout=30)
        if r.status_code != 200:
            break
        rows = r.json()
        if not rows:
            break
        out += [{"id": p["id"], "title": re.sub(r"<[^>]+>", "", p["title"]["rendered"]), "date": p["date"], "link": p["link"]} for p in rows]
        if len(rows) < 100:
            break
        page += 1
    return out


def blogger_titles():
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
            p = {"maxResults": 500, "fetchBodies": "false", "status": "LIVE"}
            if pt:
                p["pageToken"] = pt
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts", headers=h, params=p, timeout=30)
            r.raise_for_status()
            d = r.json()
            items += [{"id": x["id"], "title": x.get("title", ""), "date": x.get("published", ""), "blog_id": str(bid)} for x in d.get("items", [])]
            pt = d.get("nextPageToken")
            if not pt:
                break
        res[f"blogger_{row['site_key']}"] = items
    return res


def main():
    sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    sites = sites if isinstance(sites, list) else sites["sites"]
    data = {}
    for s in sites:
        if s["platform"] == "wordpress" and s.get("enabled", True):
            try:
                data[s["site_id"]] = wp_titles(s["url"])
            except Exception as e:
                data[s["site_id"]] = []
                print("WP FAIL", s["site_id"], e)
    try:
        data.update(blogger_titles())
    except Exception as e:
        print("BLOGGER FAIL", e)
    Path("title_audit.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("sites", len(data), "posts", sum(len(v) for v in data.values()))
    dup_in_site, firstwords, grams = [], collections.defaultdict(list), collections.Counter()
    for site, rows in data.items():
        seen = collections.defaultdict(list)
        for r in rows:
            n = norm(r["title"])
            seen[n].append(r)
            w = n.split()
            if len(w) >= 3:
                firstwords[" ".join(w[:3])].append((site, r["title"]))
            for i in range(len(w) - 2):
                grams[" ".join(w[i:i + 3])] += 1
        for n, rs in seen.items():
            if len(rs) > 1:
                dup_in_site.append((site, rs[0]["title"], len(rs)))
    print("\n== exact duplicate titles within a site:", len(dup_in_site))
    for x in sorted(dup_in_site, key=lambda x: -x[2])[:40]:
        print(x)
    print("\n== repeated first-3-word openings (>=4 posts):")
    for k, v in sorted(firstwords.items(), key=lambda kv: -len(kv[1]))[:30]:
        if len(v) >= 4:
            print(len(v), "|", k, "| e.g.", v[0][1][:70])
    print("\n== top repeated 3-grams:")
    for g, c in grams.most_common(25):
        print(c, g)


if __name__ == "__main__":
    main()
