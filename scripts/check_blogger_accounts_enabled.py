#!/usr/bin/env python3
"""Cross-check every 'connected' Blogspot site against the ACCOUNTS_TAB
sheet used by process_platform_queue.py, so a real 'enabled account not
found' failure can be told apart from a transient content-generation
failure (NoEligibleTopic etc). Prints which site_ids are missing or
disabled - these need a sheet row added/enabled, not a code fix."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from control_center.app import get_blogger_data  # noqa: E402
from gsheets_direct import get_sheets_service  # noqa: E402
from sync_automation_hub_to_sheets import ACCOUNTS_TAB  # noqa: E402


def main():
    sheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I"
    ).execute().get("values", [])
    header = values[0] if values else []
    rows = [dict(zip(header, r)) for r in values[1:]] if values else []
    by_site = {r.get("site_id"): r for r in rows}

    connected = [b for b in get_blogger_data() if b["connected"]]
    print(f"연결된 Blogspot 사이트: {len(connected)}개\n")
    missing, disabled, ok = [], [], []
    for site in connected:
        site_id = site["site_id"]
        row = by_site.get(site_id)
        if not row:
            missing.append(site_id)
        elif row.get("enabled", "ON").upper() not in {"ON", "TRUE", "1"}:
            disabled.append(site_id)
        else:
            ok.append(site_id)

    print(f"정상 등록+활성화: {len(ok)}개")
    print(f"\n시트에 계정 행 자체가 없음 ({len(missing)}개):")
    for s in missing:
        print(f"  - {s}")
    print(f"\n시트에는 있지만 enabled=OFF ({len(disabled)}개):")
    for s in disabled:
        print(f"  - {s}: {json.dumps(by_site[s], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
