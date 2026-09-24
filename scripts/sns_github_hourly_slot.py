#!/usr/bin/env python3
"""Select one of 24 SNS accounts for the current hourly GitHub slot."""
import hashlib,json,random
from datetime import datetime,timezone,timedelta
from pathlib import Path
KST=timezone(timedelta(hours=9));ROOT=Path(__file__).resolve().parents[1]
now=datetime.now(KST);policy=json.loads((ROOT/'config/sns_six_channel_policy.json').read_text(encoding='utf-8'))
rows=list(policy['accounts']);rng=random.Random(int(hashlib.sha256(('sns24|'+now.date().isoformat()).encode()).hexdigest(),16));rng.shuffle(rows)
row=rows[now.hour];row={**row,'slot_date':now.date().isoformat(),'slot_hour_kst':now.hour,'duplicate_key':f"{now.date()}|{row['platform']}|{row['role']}"}
print(json.dumps(row,ensure_ascii=False))
