import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import QUEUE_TAB

receipts = json.loads(Path('data/tistory-publishing-2026-09-07.json').read_text(encoding='utf-8'))
service = get_sheets_service()
sheet = os.environ['SHEET_ID']
values = service.spreadsheets().values().get(spreadsheetId=sheet, range=f"'{QUEUE_TAB}'!A1:Q").execute()['values']
headers = values[0]
updates = []
for receipt in receipts:
    matches = [(n, dict(zip(headers, row))) for n, row in enumerate(values[1:], 2) if len(row)>1 and row[1] == receipt['job_id']]
    assert len(matches) == 1, 'Expected exactly one queue row for '+receipt['job_id']
    n, row = matches[0]
    assert row['site_id'] == receipt['site_id'] and row['title'] == receipt['title']
    if receipt['status'] != 'published':
        if row.get('status') == 'published':
            continue
        updates += [{'range':f"'{QUEUE_TAB}'!D{n}:E{n}",'values':[['local_attention_required','FALSE']]}, {'range':f"'{QUEUE_TAB}'!L{n}:M{n}",'values':[['captcha_required','Prepared in logged-in Tistory editor; CAPTCHA pending. Do not regenerate.']]}]
        continue
    response = requests.get(receipt['public_url'], timeout=40)
    response.raise_for_status()
    assert receipt['title'] in response.text
    updates += [{'range':f"'{QUEUE_TAB}'!D{n}:E{n}",'values':[['published','FALSE']]}, {'range':f"'{QUEUE_TAB}'!J{n}:N{n}",'values':[[receipt['public_url'],receipt.get('remote_id',''),'','Public post verified without authentication; published via browser.',datetime.now(timezone.utc).isoformat()]]}]
service.spreadsheets().values().batchUpdate(spreadsheetId=sheet, body={'valueInputOption':'RAW','data':updates}).execute()
check = service.spreadsheets().values().get(spreadsheetId=sheet, range=f"'{QUEUE_TAB}'!A1:Q").execute()['values']
for receipt in receipts:
    row = next(dict(zip(headers,r)) for r in check[1:] if len(r)>1 and r[1]==receipt['job_id'])
    if receipt['status']=='published':
        assert row['status']=='published' and row['public_url']==receipt['public_url']
print('Verified and reconciled 4 public posts; final travel job held for CAPTCHA.')
