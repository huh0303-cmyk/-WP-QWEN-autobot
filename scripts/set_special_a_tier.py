#!/usr/bin/env python3
"""One-time reclassification: promote 10 proven sites (200+ daily visitors
confirmed) to a 특A tier - daily publishing (weekly_min=weekly_max=7),
random time (already handled by publish_scheduler.py's existing slot
randomization, unchanged here). Two of the ten were previously in B
(koreacrypto365, sis-korea); the rest were in A. Everything else in A/B/
NEWS is left untouched. See docs/SITE_PUBLISHING_TIERS.md for the record.
"""
import os

from gsheets_direct import get_sheets_service

SHEET_ID = os.environ.get("SHEET_ID", "").strip()
TAB = "자동화_사이트설정"

SPECIAL_A_SITE_IDS = {
    "wp_kfinance365", "wp_koreacrypto365", "wp_kskin365", "wp_ktrip365",
    "wp_kvisa365", "wp_koreawedding", "wp_sis", "wp_jobkorea365",
    "wp_jobglobal", "wp_kstudy365",
}


def _col_letter(index_0based: int) -> str:
    letters = ""
    n = index_0based + 1
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def main():
    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"'{TAB}'!A1:AE"
    ).execute().get("values", [])
    header = values[0]
    site_id_col = header.index("site_id")
    group_col = header.index("group")
    wmin_col = header.index("weekly_min")
    wmax_col = header.index("weekly_max")

    updates = []
    found = set()
    for row_index, row in enumerate(values[1:], start=2):
        if row_index and len(row) <= site_id_col:
            continue
        site_id = row[site_id_col] if len(row) > site_id_col else ""
        if site_id not in SPECIAL_A_SITE_IDS:
            continue
        found.add(site_id)
        updates.append((f"'{TAB}'!{_col_letter(group_col)}{row_index}", [["특A"]]))
        updates.append((f"'{TAB}'!{_col_letter(wmin_col)}{row_index}", [["7"]]))
        updates.append((f"'{TAB}'!{_col_letter(wmax_col)}{row_index}", [["7"]]))

    missing = SPECIAL_A_SITE_IDS - found
    if missing:
        raise SystemExit(f"site_id not found in {TAB}: {sorted(missing)}")

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "valueInputOption": "RAW",
            "data": [{"range": rng, "values": vals} for rng, vals in updates],
        },
    ).execute()
    print(f"Set group=특A, weekly_min=weekly_max=7 for {len(found)} sites:")
    for site_id in sorted(found):
        print(f"  {site_id}")


if __name__ == "__main__":
    main()
