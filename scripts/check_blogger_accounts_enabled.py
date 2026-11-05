#!/usr/bin/env python3
"""Check all enabled Blogger destinations against the platform-account sheet.

This read-only audit intentionally avoids importing the Flask control-center app,
so dashboard UI code cannot prevent a simple account-registry check from running.
"""
import json
import os
from pathlib import Path

from gsheets_direct import get_sheets_service

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = ROOT / "config" / "automation_hub_sites.json"
ACCOUNTS_TAB = "자동화_플랫폼계정"


def enabled(value):
    if isinstance(value, bool):
        return value
    return str(value if value is not None else "ON").strip().upper() not in {"OFF", "FALSE", "0", "NO"}


def main():
    sheet_id = os.environ["SHEET_ID"]
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    connected = [b for b in registry.get("sites", [])
                 if b.get("platform") == "blogger" and enabled(b.get("enabled", True))]
    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I"
    ).execute().get("values", [])
    header = values[0] if values else []
    rows = [dict(zip(header, r)) for r in values[1:]] if values else []
    by_site = {r.get("site_id"): r for r in rows if r.get("site_id")}

    print(f"등록부 활성 Blogger 사이트: {len(connected)}개")
    missing, disabled_rows, ok = [], [], []
    for site in connected:
        site_id = site["site_id"]
        row = by_site.get(site_id)
        if not row:
            missing.append(site_id)
        elif not enabled(row.get("enabled", "ON")):
            disabled_rows.append(site_id)
        else:
            ok.append(site_id)

    print(f"정상 등록+활성화: {len(ok)}개")
    print(f"시트에 계정 행 없음 ({len(missing)}개):")
    for site_id in missing:
        print(f"  - {site_id}")
    print(f"시트에 있으나 비활성 ({len(disabled_rows)}개):")
    for site_id in disabled_rows:
        print(f"  - {site_id}")
    print(json.dumps({"expected": len(connected), "ok": len(ok),
                      "missing": missing, "disabled": disabled_rows}, ensure_ascii=False))
    return 0 if not missing and not disabled_rows and len(connected) == 33 else 2


if __name__ == "__main__":
    raise SystemExit(main())
