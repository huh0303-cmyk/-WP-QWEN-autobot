"""Stable randomized KST slots; no credentials or public writes."""
import hashlib
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def plan(day):
    date.fromisoformat(day)
    policy = json.loads((ROOT / "config/meta_five_account_daily_policy.json").read_text(encoding="utf-8-sig"))
    slots = []
    # Separate morning, afternoon and evening windows avoid clustered posting.
    for platform in policy["platforms"]:
        for account in policy["accounts"]:
            key = account["key"]
            rng = random.Random(hashlib.sha256(f"{day}:{platform}:{key}".encode()).hexdigest())
            for index, (start, end) in enumerate(((490, 749), (750, 1039), (1040, 1370)), 1):
                minute = rng.randint(start, end)
                slots.append({"slot_id": f"{day}:{platform}:{key}:{index}",
                    "date_kst": day, "platform": platform, "account_key": key,
                    "expected_handle": account.get("platform_handles", {}).get(platform, account["handle"]),
                    "slot": index, "time_kst": f"{minute//60:02}:{minute%60:02}",
                    "status": "PLANNED_REQUIRES_VERIFIED_AUTH_AND_CONTENT"})
    return sorted(slots, key=lambda row: (row["time_kst"], row["slot_id"]))

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"timezone": "Asia/Seoul", "slots": plan(args.date)}, indent=2)+"\n", encoding="utf-8")
    print("PLANNED=30; PUBLICATION_PERFORMED=false")
