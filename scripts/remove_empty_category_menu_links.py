#!/usr/bin/env python3
"""One-off: remove menu links that point to empty (0-post) categories, across
the 25 general WP blog sites. Does NOT touch the category taxonomy itself
(pick_best_category() still needs the 'Etc' fallback to exist) — only removes
the dead-end nav link so visitors/reviewers never land on a blank category
page. Two newsroom sites (koreanews365, theseouljournal) are excluded: their
categories are actively populated and structured differently."""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from site_registry import ACTIVE_SITES

WP_USER = "huh0303@gmail.com"
EXCLUDE = {"https://koreanews365.com", "https://theseouljournal.com"}
OUT = ROOT / "artifacts/empty-category-menu-cleanup.json"


def main():
    results = []
    for site, env_name, _lifecycle in ACTIVE_SITES:
        if site in EXCLUDE:
            continue
        pw = os.environ.get(env_name, "")
        if not pw:
            results.append({"site": site, "status": "skip_no_secret"})
            continue
        auth = (WP_USER, pw)
        try:
            cats = requests.get(f"{site}/wp-json/wp/v2/categories", params={"per_page": 100}, timeout=20).json()
            empty_ids = {c["id"] for c in cats if isinstance(c, dict) and c.get("count", 0) == 0}
            if not empty_ids:
                results.append({"site": site, "status": "no_empty_categories"})
                continue
            items = requests.get(f"{site}/wp-json/wp/v2/menu-items", auth=auth, params={"per_page": 100}, timeout=20).json()
            if not isinstance(items, list):
                results.append({"site": site, "status": "failed", "error": str(items)[:300]})
                continue
            removed = []
            for item in items:
                if item.get("object") == "category" and item.get("object_id") in empty_ids:
                    del_resp = requests.delete(
                        f"{site}/wp-json/wp/v2/menu-items/{item['id']}",
                        auth=auth, params={"force": "true"}, timeout=20,
                    )
                    removed.append({
                        "menu_item_id": item["id"],
                        "title": item.get("title", {}).get("rendered", ""),
                        "menu": item.get("menus"),
                        "status": del_resp.status_code,
                    })
            results.append({"site": site, "status": "done", "empty_categories": len(empty_ids), "menu_links_removed": len(removed), "detail": removed})
        except Exception as exc:
            results.append({"site": site, "status": "failed", "error": str(exc)[:300]})
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    failed = [r for r in results if r["status"] == "failed"]
    if failed:
        raise SystemExit(f"{len(failed)} site(s) failed: {[r['site'] for r in failed]}")


if __name__ == "__main__":
    main()
