"""k-health365.com: 301로 이미 이전된 글 40개를 Rank Math noindex로 설정해 사이트맵에서 제외.
글 상태·리다이렉트는 변경하지 않는다(메타 robots만). DRY_RUN=true면 읽기만."""
import json, os, re, sys
import requests

BASE = "https://k-health365.com"
IDS = [3374,3386,3392,3410,3574,3704,3708,3718,3750,3843,3863,3871,3875,3879,3924,3936,3938,3951,3973,3975,3977,
       4036,4038,4042,4798,5528,5531,5764,5768,5772,5773,5776,5786,5866,5868,5889,5891,5894,5903,5916]
AUTH = ("huh0303@gmail.com", os.environ["KHEALTH365COM"])
DRY = os.getenv("DRY_RUN", "true").lower() != "false"
NOIDX = ["noindex", "follow"]
H = {"User-Agent": "Mozilla/5.0 london-project-claude"}


def robots_of(pid):
    r = requests.get(f"{BASE}/wp-json/wp/v2/posts/{pid}?context=edit&_fields=id,link,status,meta", auth=AUTH, timeout=30, headers=H)
    r.raise_for_status()
    j = r.json()
    return j, (j.get("meta") or {}).get("rank_math_robots")


def sitemap_urls():
    out = set()
    idx = requests.get(BASE + "/sitemap_index.xml", timeout=30, headers=H).text
    for sm in re.findall(r"<loc>([^<]+)</loc>", idx):
        if "post-sitemap" in sm:
            t = requests.get(sm, timeout=30, headers=H).text
            out.update(re.findall(r"<loc>([^<]+)</loc>", t))
    return out


def main():
    before = sitemap_urls()
    res = {"dry_run": DRY, "sitemap_before": len(before), "items": []}
    links = {}
    for pid in IDS:
        row = {"id": pid}
        try:
            j, rb = robots_of(pid)
            links[pid] = j.get("link")
            row.update(status=j.get("status"), link=j.get("link"), robots_before=rb, in_sitemap_before=j.get("link") in before)
            if not DRY and j.get("status") == "publish":
                r = requests.post(f"{BASE}/wp-json/wp/v2/posts/{pid}", auth=AUTH, headers=H, timeout=30, json={"meta": {"rank_math_robots": NOIDX}})
                row["rest_http"] = r.status_code
                _, ra = robots_of(pid)
                if not (ra and "noindex" in ra):
                    r2 = requests.post(f"{BASE}/wp-json/rankmath/v1/updateMeta", auth=AUTH, headers=H, timeout=30,
                                       json={"objectID": pid, "objectType": "post", "meta": {"rank_math_robots": NOIDX}})
                    row["rankmath_http"] = r2.status_code
                    _, ra = robots_of(pid)
                row["robots_after"] = ra
        except Exception as e:
            row["error"] = str(e)[:200]
        res["items"].append(row)
    after = sitemap_urls()
    res["sitemap_after"] = len(after)
    res["still_in_sitemap"] = [p for p, l in links.items() if l in after]
    res["noindex_confirmed"] = sum(1 for i in res["items"] if i.get("robots_after") and "noindex" in i["robots_after"])
    print(json.dumps({k: v for k, v in res.items() if k != "items"}, ensure_ascii=False))
    json.dump(res, open("khealth_noindex_result.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
