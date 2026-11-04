#!/usr/bin/env python3
"""Audit that every registered WordPress/Blogspot site has ten verified offers."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from automation_hub.coupang_partners import load_candidates
registry = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
shared_data = json.loads((ROOT / "data/affiliate/global-coupang-product-pool.json").read_text(encoding="utf-8"))
shared_products = shared_data.get("products", [])
shared_counts = {}
for product in shared_products:
    category = product.get("category", "unknown")
    shared_counts[category] = shared_counts.get(category, 0) + 1
rows = []
for site in registry.get("sites", []):
    site_id = site["site_id"]
    offers = load_candidates(site_id)
    rows.append({
        "site_id": site_id,
        "platform": site.get("platform", ""),
        "url": site.get("url", ""),
        "verified_unique_products": len(offers),
        "required": 10,\n        "shared_pool_products": len(shared_products),
        "status": "READY" if len(offers) >= 10 else "NEEDS_CATALOG",
        "missing": max(0, 10 - len(offers)),
    })
report = {
    "required_products_per_post": 10,\n    "global_pool_target": 200,\n    "global_pool_products": len(shared_products),\n    "global_pool_category_counts": shared_counts,\n    "global_pool_shortfall": max(0, 200 - len(shared_products)),
    "registered_sites": len(rows),
    "ready_sites": sum(x["status"] == "READY" for x in rows),
    "needs_catalog_sites": sum(x["status"] != "READY" for x in rows),
    "sites": rows,
}
out = ROOT / "reports/coupang-catalog-coverage.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("required_products_per_post", "global_pool_target", "global_pool_products", "global_pool_shortfall", "registered_sites", "ready_sites", "needs_catalog_sites")}, ensure_ascii=False))
for row in rows:
    if row["status"] != "READY":
        print(f"NEEDS_CATALOG {row['site_id']} {row['verified_unique_products']}/10")
