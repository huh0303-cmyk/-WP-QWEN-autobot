"""Deterministic randomized KST posting slots for the 12 Meta destinations."""
import hashlib
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/meta_12_account_daily_policy.json"

def plan(day):
    date.fromisoformat(day)
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    windows = policy["daily_cadence"]["slot_windows_kst"]
    slots = []
    for account in policy["accounts"]:
        for platform in policy["platforms"]:
            handle = account[platform]
            destination = f"{platform}:{account['key']}"
            for index, (start, end) in enumerate(windows, 1):
                seed = hashlib.sha256(f"{day}:{destination}:{index}".encode()).hexdigest()
                rng = random.Random(seed)
                sh, sm = map(int, start.split(":"))
                eh, em = map(int, end.split(":"))
                minute = rng.randint(sh * 60 + sm, eh * 60 + em)
                slots.append({
                    "slot_id": f"{day}:{destination}:{index}",
                    "date_kst": day,
                    "account_key": account["key"],
                    "platform": platform,
                    "expected_handle": handle,
                    "slot": index,
                    "time_kst": f"{minute // 60:02}:{minute % 60:02}"
                })
    return sorted(slots, key=lambda x: (x["time_kst"], x["slot_id"]))

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    args = p.parse_args()
    print(json.dumps({"timezone": "Asia/Seoul", "slots": plan(args.date)}, indent=2))