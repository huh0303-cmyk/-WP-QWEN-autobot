#!/usr/bin/env python3
"""Priority restore for oliveyoungkorea.com and kskin365.com.
Restore only private posts whose current Google URL Inspection verdict is PASS.
"""
import json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restore_indexed_private_posts import (
    fetch_private_posts, inspect_url, publish, property_for, title_of,
    get_gsc_token, gsc_get, WP_USER
)

TARGETS = [
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kskin365.com", "KSKIN365COM"),
]
OUT = "restore_priority_olive_kskin_result.json"

def save(x):
    x["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(x, f, ensure_ascii=False, indent=2)

def main():
    result = {"started_at": datetime.now(timezone.utc).isoformat(), "sites": {}}
    tok = get_gsc_token()
    r = gsc_get(tok, "/sites")
    if r.status_code != 200:
        raise RuntimeError(f"GSC sites HTTP {r.status_code}: {r.text[:200]}")
    accessible = {x.get("siteUrl") for x in r.json().get("siteEntry", []) if x.get("siteUrl")}

    for site, secret in TARGETS:
        domain = site.replace("https://", "")
        row = {"private_before": 0, "restored_indexed": 0, "kept_private_unindexed": 0,
               "kept_private_uncertain": 0, "publish_failed": 0, "items": []}
        result["sites"][domain] = row
        pw = os.getenv(secret, "").strip()
        if not pw:
            row["status"] = "SKIP_NO_SECRET"; save(result); continue
        prop = property_for(domain, site, accessible)
        row["gsc_property"] = prop
        if not prop:
            row["status"] = "SKIP_NO_GSC_PROPERTY"; save(result); continue
        posts = fetch_private_posts(site, pw)
        row["private_before"] = len(posts)
        print(f"=== {domain}: PRIVATE {len(posts)} ===", flush=True)
        for p in posts:
            item = {"id": p.get("id"), "url": p.get("link"), "title": title_of(p)}
            ins = inspect_url(tok, prop, p.get("link"))
            item["inspection"] = ins
            if not ins.get("ok"):
                item["decision"] = "KEEP_PRIVATE_UNCERTAIN"
                row["kept_private_uncertain"] += 1
            elif ins.get("verdict") == "PASS":
                ok, code, detail = publish(site, pw, p["id"])
                if ok:
                    item["decision"] = "RESTORED_PUBLISH_INDEXED"
                    row["restored_indexed"] += 1
                    print(f"RESTORED {domain} #{p['id']} {item['title'][:90]}", flush=True)
                else:
                    item["decision"] = "RESTORE_FAILED"
                    item["http"] = code; item["error"] = detail
                    row["publish_failed"] += 1
            else:
                item["decision"] = "KEEP_PRIVATE_UNINDEXED"
                row["kept_private_unindexed"] += 1
            row["items"].append(item)
            save(result)
            time.sleep(1.05)
        row["status"] = "OK"
        row["private_after_expected"] = row["private_before"] - row["restored_indexed"]
        save(result)

    result["totals"] = {
        "private_before": sum(v.get("private_before",0) for v in result["sites"].values()),
        "restored_indexed": sum(v.get("restored_indexed",0) for v in result["sites"].values()),
        "kept_private_unindexed": sum(v.get("kept_private_unindexed",0) for v in result["sites"].values()),
        "kept_private_uncertain": sum(v.get("kept_private_uncertain",0) for v in result["sites"].values()),
        "publish_failed": sum(v.get("publish_failed",0) for v in result["sites"].values()),
    }
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    save(result)
    print(json.dumps(result["totals"], ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
