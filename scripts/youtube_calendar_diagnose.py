"""Read-only forensic check of malformed YouTube calendar row; never modify Sheets."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[0]))
from gsheets_direct import get_sheets_service
from automation_hub.youtube_calendar import TAB
s=get_sheets_service()
sheet=os.environ["SHEET_ID"]
rows=s.spreadsheets().values().get(spreadsheetId=sheet,range="'"+TAB+"'!A2:O").execute().get("values",[])
index=2593-2
row=rows[index] if index<len(rows) else []
rid=row[0] if row else ""
duplicates=[i+2 for i,r in enumerate(rows) if r and r[0]==rid] if rid else []
print({"sheet_row":2593,"schedule_id":rid,"date":row[1] if len(row)>1 else "",
"platform":row[2] if len(row)>2 else "","channel":row[3] if len(row)>3 else "",
"status":row[12] if len(row)>12 else "","duplicate_id_rows":duplicates[:20],
"total_rows":len(rows)})

for i in duplicates:
    v=rows[i-2]
    print({"row":i,"id":v[0],"date":v[1],"channel":v[3],"status":v[12] if len(v)>12 else "","topic":v[7][:100] if len(v)>7 else ""})
