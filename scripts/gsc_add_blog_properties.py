#!/usr/bin/env python3
from __future__ import annotations
import json, os
from urllib.parse import quote
import requests

TARGETS = [
    "https://k-vietnam.tistory.com/",
    "https://k-insight-vietnam.tistory.com/",
    "https://k-healthcare.tistory.com/",
    "https://huh0303.tistory.com/",
    "https://k-trip365.tistory.com/",
    "https://blog.naver.com/huh0303",
    "https://blog.naver.com/huh3",
    "https://blog.naver.com/huh4",
]

def main():
    token = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_METRICS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_METRICS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_METRICS_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    token.raise_for_status()
    headers={"Authorization":"Bearer "+token.json()["access_token"]}
    rows=[]
    for site in TARGETS:
        url="https://www.googleapis.com/webmasters/v3/sites/"+quote(site,safe="")
        r=requests.put(url,headers=headers,timeout=30)
        rows.append({"site":site,"add_status":r.status_code,"add_ok":r.status_code in (200,204)})
    listing=requests.get("https://www.googleapis.com/webmasters/v3/sites",headers=headers,timeout=30)
    listing.raise_for_status()
    perms={x.get("siteUrl"):x.get("permissionLevel") for x in listing.json().get("siteEntry",[])}
    for row in rows:
        row["permission"]=perms.get(row["site"])
    print(json.dumps({"rows":rows},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
