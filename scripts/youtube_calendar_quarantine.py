"""One-time guarded non-destructive quarantine of exact duplicate calendar rows."""
import json,os,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[0])]
from gsheets_direct import get_sheets_service
from automation_hub.youtube_calendar import TAB,READY,parse_calendar
s=get_sheets_service(); sid=os.environ["SHEET_ID"]
indices=[2588,2593,2598]
data=[]
for i in indices:
    value=s.spreadsheets().values().get(spreadsheetId=sid,range=f"'{TAB}'!A{i}:O{i}").execute().get("values",[])
    r=(value[0] if value else [])+[""]*15
    data.append(r[:15])
expected="HEALING-20261113-1400"
first=data[0]
for idx,row in zip(indices,data):
    assert row[0]==expected,(idx,"id_changed")
    assert row[1]=="2026-11-13 14:00 KST",(idx,"date_changed")
    assert row[2]=="YouTube Playlist",(idx,"platform_changed")
    assert row[3]=="Healing",(idx,"channel_changed")
    assert row[7]==first[7],(idx,"topic_changed")
    assert row[12]==READY,(idx,"status_changed")
    assert not row[13] and "[yt-calendar:" not in row[14],(idx,"claimed_or_uploaded")
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/youtube-calendar-quarantine-backup.json").write_text(json.dumps({"rows":dict(zip(indices,data))},ensure_ascii=False,indent=2),encoding="utf-8")
print("BACKUP_OK:",indices)
if os.getenv("APPLY","false").lower()!="true":
    print("DRY_RUN_ONLY")
    raise SystemExit(0)
changes=[]
for i in indices[1:]:
    changes.extend([{"range":f"'{TAB}'!C{i}","values":[["보류-중복"]]},
                    {"range":f"'{TAB}'!M{i}","values":[["보류"]]}])
s.spreadsheets().values().batchUpdate(spreadsheetId=sid,body={"valueInputOption":"RAW","data":changes}).execute()
for i in indices[1:]:
    row=s.spreadsheets().values().get(spreadsheetId=sid,range=f"'{TAB}'!C{i}:M{i}").execute()["values"][0]
    assert row[0]=="보류-중복" and row[10]=="보류"
print("QUARANTINED_DUPLICATES_VERIFIED: rows 2593 and 2598; canonical 2588 unchanged")
