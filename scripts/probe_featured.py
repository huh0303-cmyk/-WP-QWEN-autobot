import json, re, sys, requests
UA = {"User-Agent": "Mozilla/5.0 (probe)"}
ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sites = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
sites = sites if isinstance(sites, list) else sites["sites"]
url = {s["site_id"]: s["url"] for s in sites}
for arg in sys.argv[1:]:
    site, pid = arg.split(":")
    u = url[site]
    r = requests.get(f"{u}/wp-json/wp/v2/posts/{pid}", params={"_embed": "wp:featuredmedia"}, headers=UA, timeout=40)
    d = r.json()
    emb = d.get("_embedded", {}).get("wp:featuredmedia", [])
    print(site, pid, "feat_id", d.get("featured_media"), "embed", [ (e.get("source_url") or e.get("code") or str(e)[:80]) for e in emb])
    m = requests.get(f"{u}/wp-json/wp/v2/media/{d.get('featured_media')}", headers=UA, timeout=40)
    print("  media GET", m.status_code, (m.json().get("source_url") if m.ok else m.text[:100]))
    h = requests.get(d["link"], headers=UA, timeout=40).text
    print("  page imgs with uploads/pexels:", len(re.findall(r'(?:pexels|pixabay)-\d+', h)), "og:image:", re.findall(r'og:image" content="([^"]+)', h)[:1])
