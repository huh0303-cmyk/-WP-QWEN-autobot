#!/usr/bin/env python3
"""Synchronize all 33 Blogger execution rooms from the canonical profile map."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "config" / "automation_rooms.json"
PROFILES_PATH = ROOT / "config" / "content_engine_profiles.json"

ROOM_TO_KEY = {
    "blogger_khealth365": "khealth365",
    "blogger_koreamedicaltour365": "medicaltour",
    "blogger_koreainvest365": "kinvest365",
    "blogger_kikorea": "kikorea",
    "blogger_koreainsurance365": "kinsurance365",
    "blogger_kfinance365": "kfinance365",
    "blogger_koreataxnlaw": "koreataxlaw",
    "blogger_koreacrypto365": "kcrypto365",
    "blogger_krealestate365": "krealestate",
    "blogger_ktech365": "ktech365",
    "blogger_kskin365": "kskin365",
    "blogger_oliveyoungkorea": "oliveyoung",
    "blogger_kworld365": "kworld365",
    "blogger_ktrip365": "ktrip365",
    "blogger_kvisa365": "kvisa365",
    "blogger_koreawedding365": "koreawedding",
    "blogger_kstudy365": "kstudy365",
    "blogger_studyinkorea365": "studyinkorea",
    "blogger_kieca": "kieca",
    "blogger_ksa": "ksa",
    "blogger_sis": "sis",
    "blogger_jobkorea365": "jobkorea365",
    "blogger_jobinkorea365": "jobinkorea",
    "blogger_jobkoreaglobal": "jobglobal",
    "blogger_korea365": "korea365",
    "blogger_koreanews365": "koreanews",
    "blogger_theseouljournal": "seouljournal",
    "blogger_kwellness_lab": "kwellness_lab",
    "blogger_kmedical_job_center": "kmedical_job_center",
    "blogger_korea_life_support365": "korea_life_support365",
    "blogger_koreamedicaltour1": "koreamedicaltour1",
    "blogger_kworld365_kpop": "kworld365_kpop",
    "blogger_seoul_intl_school_guide": "seoul_intl_school_guide",
}


def main() -> int:
    data = json.loads(ROOMS_PATH.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    by_key = {profile["site_key"]: profile for profile in profiles}
    updated = 0
    for room in data.get("rooms", []):
        if room.get("platform") != "blogger":
            continue
        site_key = ROOM_TO_KEY.get(room.get("room_id", ""))
        profile = by_key.get(site_key or "")
        if not profile or not profile["blogspot"].get("ready_for_automation"):
            raise SystemExit(f"Cannot ready {room.get('room_id')}: canonical Blogger mapping missing")
        room["source_id"] = profile.get("source_site_id") or f"wp_{site_key}"
        room["destination_id"] = profile["blogspot"]["destination_id"]
        room["enabled"] = True
        room["status"] = "READY"
        room["publish_policy"] = "draft"
        room["duplicate_guard"] = True
        updated += 1
    if updated != 33:
        raise SystemExit(f"Expected 33 Blogger rooms, updated {updated}")
    ROOMS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "blogger_rooms_ready": updated}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
