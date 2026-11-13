#!/usr/bin/env python3
"""Rotate the weekly Coupang catalog from a separately verified candidate file.

Never fabricate affiliate links or extend expired offers automatically.
"""
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
current_path = ROOT / "config/affiliate/global-weekly-10.json"
candidate_path = ROOT / "config/affiliate/next-weekly-10-verified.json"
current = json.loads(current_path.read_text(encoding="utf-8"))
now = datetime.now(ZoneInfo("Asia/Seoul"))
end = datetime.fromisoformat(current["lock_window"]["ends_at"])
if now < end:
    print(f"Not due until {end.isoformat()}")
    raise SystemExit(0)
if not candidate_path.exists():
    raise SystemExit("ROTATION_BLOCKED: missing independently verified next-weekly-10-verified.json")
next_set = json.loads(candidate_path.read_text(encoding="utf-8"))
# Popularity is optional. Without verified rankings, uniformly sample across ALL
# SeoulMall categories; never fabricate popularity or product links.
if next_set.get("source") not in ("seoulmall_verified_popularity_export", "seoulmall_verified_product_export"):
    raise SystemExit("ROTATION_BLOCKED: require an authenticated SeoulMall product export")
if next_set.get("storefront_url") not in (
    "https://influencers.coupang.com/s/seoulmall",
    "https://influencers.coupang.com/s/seoulshop",
):
    raise SystemExit("ROTATION_BLOCKED: unknown SeoulMall storefront URL")
if next_set.get("owner_approved") is not True or next_set.get("source_of_truth") is not True:
    raise SystemExit("ROTATION_BLOCKED: next set not approved")
pool = next_set.get("items", [])
old_urls = {x["url"] for x in current["items"]}
eligible = []
seen_urls, seen_images = set(), set()
for x in pool:
    url, image = x.get("url", ""), x.get("image_url", "")
    if (not x.get("enabled") or not x.get("affiliate_confirmed")
            or not url.startswith("https://link.coupang.com/")
            or "/image/affiliate/banner/" not in image
            or url in old_urls or url in seen_urls or image in seen_images):
        continue
    seen_urls.add(url)
    seen_images.add(image)
    eligible.append(x)
if len(eligible) < 10:
    raise SystemExit("ROTATION_BLOCKED: fewer than 10 unique verified new SeoulMall products")
rng = random.Random(now.strftime("%Y-%m-%d") + ":" + current["set_id"])
ranked = all(isinstance(x.get("popularity_rank"), int) and x["popularity_rank"] > 0 for x in eligible)
selected = []
for _ in range(10):
    weights = [1 / x["popularity_rank"] ** 0.7 for x in eligible] if ranked else None
    pick = rng.choices(eligible, weights=weights, k=1)[0] if ranked else rng.choice(eligible)
    selected.append(pick)
    eligible.remove(pick)
items = selected
archive = ROOT / "config/affiliate/archive"
archive.mkdir(parents=True, exist_ok=True)
(archive / (current["set_id"] + ".json")).write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
current["items"] = [{k: v for k, v in x.items() if k != "popularity_rank"} for x in items]
current["set_id"] = "global-week-" + now.strftime("%Y-%m-%d")
current["lock_window"] = {"starts_at": now.isoformat(), "ends_at": (now + timedelta(days=7)).isoformat(), "duration_hours": 168}
current["rotation_policy"]["next_rotation_due"] = current["lock_window"]["ends_at"]
current["rotation_policy"]["next_set_status"] = "pending_verified_account_generated_products"
current.pop("extension", None)
current_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
candidate_path.unlink()
print("ROTATED: new approved set committed to working tree")
