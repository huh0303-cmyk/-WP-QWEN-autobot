#!/usr/bin/env python3
"""One-shot: CEO said 모두활성 (activate all) for the 3 Blogger accounts that
were left disabled pending a numeric Blog ID check. automation_hub_sites.json
already has a real destination_id for all three (korea365's was resolved
since the hold note was written but never synced back to this sheet row) -
this fills it in and flips enabled to ON. Never touches any other row."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from gsheets_direct import get_sheets_service  # noqa: E402
from sync_automation_hub_to_sheets import ACCOUNTS_TAB  # noqa: E402

SITE_IDS_TO_ACTIVATE = {"blogger_korea365", "blogger_kfinance365", "blogger_kieca"}


def main():
    sheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()
    registry = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
    by_site_id = {s["site_id"]: s for s in registry["sites"] if s.get("platform") == "blogger"}

    values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I",
    ).execute().get("values", [])
    header = values[0]
    updates = []
    for row_index, row in enumerate(values[1:], start=2):
        row_dict = dict(zip(header, row))
        site_id = row_dict.get("site_id", "")
        if site_id not in SITE_IDS_TO_ACTIVATE:
            continue
        fresh = by_site_id.get(site_id, {})
        destination_id = str(fresh.get("destination_id") or row_dict.get("destination_id") or "")
        if not destination_id:
            print(f"SKIP {site_id}: still no destination_id anywhere, cannot activate")
            continue
        new_row = [
            row_dict.get("account_id", f"blogger:{site_id}"), "blogger", site_id,
            row_dict.get("display_name", site_id), destination_id,
            fresh.get("url", row_dict.get("editor_url", "")),
            row_dict.get("auth_profile", "default"), "ON",
            "activated 2026-09-07: destination_id confirmed in automation_hub_sites.json",
        ]
        updates.append({"range": f"'{ACCOUNTS_TAB}'!A{row_index}:I{row_index}", "values": [new_row]})
        print(f"ACTIVATE {site_id}: destination_id={destination_id}")

    if updates:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "RAW", "data": updates},
        ).execute()
    print(f"Updated {len(updates)} row(s)")


if __name__ == "__main__":
    main()
