#!/usr/bin/env python3
"""Rotate the weekly Coupang catalog from a separately verified candidate file.

Never fabricate affiliate links or extend expired offers automatically.
"""
import json
import os
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
if next_set.get("owner_approved") is not True or next_set.get("source_of_truth") is not True:
    raise SystemExit("ROTATION_BLOCKED: next set not approved")
items = next_set.get("items", [])
old_urls = {x["url"] for x in current["items"]}
counts = {"k_beauty_skincare": 0, "health_functional_foods": 0}
urls, images = set(), set()
for x in items:
    url, image = x.get("url", ""), x.get("image_url", "")
    category = x.get("category", "")
    if (category not in counts or not x.get("enabled") or not x.get("affiliate_confirmed")
            or not url.startswith("https://link.coupang.com/")
            or "/image/affiliate/banner/" not in image
            or url in old_urls or url in urls or image in images):
        raise SystemExit(f"ROTATION_BLOCKED: invalid or reused offer: {x.get('id', '?')}")
    urls.add(url); images.add(image); counts[category] += 1
if len(items) != 10 or counts != {"k_beauty_skincare": 5, "health_functional_foods": 5}:
    raise SystemExit("ROTATION_BLOCKED: exactly five beauty and five health offers required")
archive = ROOT / "config/affiliate/archive"
archive.mkdir(parents=True, exist_ok=True)
(archive / (current["set_id"] + ".json")).write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
current["items"] = items
current["set_id"] = "global-week-" + now.strftime("%Y-%m-%d")
current["lock_window"] = {"starts_at": now.isoformat(), "ends_at": (now + timedelta(days=7)).isoformat(), "duration_hours": 168}
current["rotation_policy"]["next_rotation_due"] = current["lock_window"]["ends_at"]
current["rotation_policy"]["next_set_status"] = "pending_verified_account_generated_products"
current.pop("extension", None)
current_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
candidate_path.unlink()
print("ROTATED: new approved set committed to working tree")
