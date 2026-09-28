#!/usr/bin/env python3
from __future__ import annotations
import json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
KST=timezone(timedelta(hours=9))

def main():
    data={
        "client_id":os.environ["GOOGLE_METRICS_CLIENT_ID"],
        "client_secret":os.environ["GOOGLE_METRICS_CLIENT_SECRET"],
        "refresh_token":os.environ["GOOGLE_METRICS_REFRESH_TOKEN"],
        "grant_type":"refresh_token",
    }
    token=requests.post("https://oauth2.googleapis.com/token",data=data,timeout=30)
    token.raise_for_status()
    headers={"Authorization":"Bearer "+token.json()["access_token"]}
    response=requests.get("https://www.googleapis.com/webmasters/v3/sites",headers=headers,timeout=30)
    response.raise_for_status()
    rows=sorted(response.json().get("siteEntry",[]),key=lambda x:x.get("siteUrl",""))
    payload={"generated_at":datetime.now(KST).isoformat(),"count":len(rows),"properties":rows}
    out=ROOT/"data/gsc_properties.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"count":len(rows),"sample":[x.get("siteUrl") for x in rows[:20]]},ensure_ascii=False))

if __name__=="__main__":
    main()
