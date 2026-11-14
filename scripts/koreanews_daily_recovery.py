"""Bounded Koreanews recovery; authenticated KST daily quota and durable receipts."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta
import requests

SITE = "https://koreanews365.com"
def inventory():
    midnight = datetime.now(timezone(timedelta(hours=9))).replace(hour=0, minute=0, second=0, microsecond=0)
    r = requests.get(SITE + "/wp-json/wp/v2/posts",
        auth=("huh0303@gmail.com", os.environ["KOREANEWS365COM"]),
        params={"status": "publish", "after": midnight.astimezone(timezone.utc).isoformat(),
                "per_page": 100, "_fields": "id,link,title,featured_media,date"}, timeout=45)
    r.raise_for_status()
    return r.json()

def main():
    if os.getenv("TARGET_SITE_URL", "").rstrip("/") != SITE:
        raise RuntimeError("Koreanews-only runner")
    env = os.environ.copy()
    before = inventory()
    target = min(5, len(before) + 1)
    attempts = []
    for i in range(10):
        current = inventory()
        if len(current) >= target:
            break
        day = datetime.now(timezone(timedelta(hours=9))).date().toordinal()
        politics, sports, world = ("정치", "스포츠", "글로벌")
        # Seven Korean politics slots across each two-day cycle.
        desks = (politics, politics, sports, politics, world) if day % 2 else (
            politics, politics, world if (day // 2) % 2 else sports, politics, politics
        )
        if not env.get("NEWSROOM_SOURCE_URL") and not env.get("NEWSROOM_PREFERRED_CATEGORY"):
            env["NEWSROOM_SUGGESTED_CATEGORY"] = desks[len(current)]
        result = subprocess.run([sys.executable, "-u", "scripts/autopost_current.py"], env=env)
        attempts.append({"attempt": i + 1, "returncode": result.returncode})
        if Path("newsroom_publish_result.json").exists():
            Path(f"artifacts/newsroom-result-{i+1}.json").write_text(
                Path("newsroom_publish_result.json").read_text(encoding="utf-8"), encoding="utf-8")
    final = inventory()
    receipt = {"before": before, "after": final, "target": target, "attempts": attempts}
    Path("artifacts/koreanews-daily-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    if len(final) < target:
        raise RuntimeError(f"Daily target unmet: {len(final)}/{target}")
if __name__ == "__main__":
    main()
