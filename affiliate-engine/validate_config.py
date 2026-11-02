import json
from pathlib import Path

cfg = json.loads(Path("affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8"))
slots = cfg["required_slots"]
assert len(slots) == 10, f"Expected 10 slots, got {len(slots)}"
assert sum(x["count"] for x in slots) == 10, "Slot count must total 10"
assert cfg["affiliate_programs"]["coupang_partners"]["enabled"] is True
assert cfg["safety_gates"]["require_real_tracking_url"] is True
assert cfg["safety_gates"]["never_delete_posts"] is True
assert cfg["publishing_policy"]["wordpress"]["preserve_existing_body"] is True
assert cfg["publishing_policy"]["blogger"]["preserve_existing_body"] is True
assert cfg["new_content_automation"]["scheduled_mode"] == "dry_run"
assert cfg["new_content_automation"]["manual_write_requires"] == "AFFILIATE_WRITE_ENABLED=true"
print("AFFILIATE_CONFIG_VALID=PASS")
print("REQUIRED_PRODUCT_SLOTS=10")
print("COUPANG_MANDATORY=PASS")
print("WORDPRESS_APPEND_ONLY=PASS")
print("BLOGGER_APPEND_ONLY=PASS")
print("LIVE_PUBLISH=NOT_ENABLED")
print("NEW_CONTENT_SCHEDULE=DRY_RUN_ONLY")
