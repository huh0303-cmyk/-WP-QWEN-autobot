"""Read-only audit: repeated opening sentences + posts with no image (WP + Blogger, bodies included)."""
from __future__ import annotations
import collections, html, json, os, re, sys, time
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_titles_images_v2 import ROOT, get, clean, IMG_RE, SKIP_IMG  # noqa: E402

TAG = re.compile(r"<(script|style|figure|figcaption)\b.*?</\1>", re.S | re.I)


def first_sentence(body: str) -> str:
    t = TAG.sub(" ", body or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    m = re.search(r"(.{15,}?[.!?。])(\s|$)", t)
    return (m.group(1) if m else t[:160]).strip()


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣ぁ-んァ-ン一-龥 ]", "", s.lower()).strip()


def imgs_of(body: str) -> list[str]:
    return [u for u in IMG_RE.findall(body or "") if not any(x in u.lower() for x in SKIP_IMG)]


def wp(url):
    out, page = [], 1
    while page <= 40:
        r = get(f"{url}/wp-json/wp/v2/posts", params={"per_page": 50, "page": page, "status": "publish",
                "_fields": "id,title,link,featured_media,content"})
        if r.status_code != 200:
            break
        rows = r.json()
        if not rows:
            break
        for p in rows:
            b = p["content"]["rendered"]
            out.append({"id": p["id"], "title": clean(p["title"]["rendered"]), "link": p["link"],
                        "opening": first_sentence(b), "feat": int(p.get("featured_media") or 0), "imgs": len(imgs_of(b))})
        if len(rows) < 50:
            break
        page += 1
    return out


def blogger():
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
            p = {"maxResults": 100, "fetchBodies": "true", "status": "LIVE", "fields": "nextPageToken,items(id,title,url,content)"}
            if pt:
                p["pageToken"] = pt
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts", headers=h, params=p, timeout=60)
            r.raise_for_status()
            d = r.json()
            for x in d.get("items", []):
                b = x.get("content", "")
                items.append({"id": x["id"], "title": clean(x.get("title", "")), "link": x.get("url", ""),
                              "opening": first_sentence(b), "feat": 0, "imgs": len(imgs_of(b)), "blog_id": str(bid)})
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
                data[s["site_id"]] = wp(s["url"])
            except Exception as e:  # noqa: BLE001
                data[s["site_id"]] = []
                print("WP FAIL", s["site_id"], type(e).__name__, flush=True)
    try:
        data.update(blogger())
    except Exception as e:  # noqa: BLE001
        print("BLOGGER FAIL", type(e).__name__, str(e)[:160], flush=True)
    print(f"sites={len(data)} posts={sum(len(v) for v in data.values())}")
    exact, pref = collections.defaultdict(list), collections.defaultdict(list)
    noimg = {}
    for site, rows in data.items():
        noimg[site] = [r["id"] for r in rows if not r["feat"] and not r["imgs"]]
        for r in rows:
            n = norm(r["opening"])
            if len(n) < 12:
                continue
            exact[(site, n)].append(r["id"])
            pref[(site, " ".join(n.split()[:5]))].append(r["id"])
    ex = [{"site": k[0], "opening": k[1], "ids": v} for k, v in exact.items() if len(v) >= 2]
    pf = [{"site": k[0], "prefix": k[1], "n": len(v), "ids": v} for k, v in pref.items() if len(v) >= 3]
    pf.sort(key=lambda x: -x["n"])
    print("exact_same_opening_within_site groups:", len(ex), "posts:", sum(len(x["ids"]) for x in ex))
    print("same_first5words(>=3) groups:", len(pf), "posts:", sum(x["n"] for x in pf))
    for x in pf[:25]:
        print("  ", x["site"], x["n"], x["prefix"])
    print("no image per site:", {k: f"{len(v)}/{len(data[k])}" for k, v in noimg.items() if v})
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/openings_audit_v3.json").write_text(json.dumps(
        {"posts": data, "exact": ex, "prefix": pf, "no_image": noimg}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
