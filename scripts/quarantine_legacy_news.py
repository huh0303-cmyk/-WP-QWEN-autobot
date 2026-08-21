#!/usr/bin/env python3
"""Quarantine all pre-relaunch published posts on the two newsroom sites."""
from __future__ import annotations
import argparse,json,os
from datetime import datetime,timezone
from pathlib import Path
import requests

USER=os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
ENV={"koreanews365.com":"KOREANEWS365COM","theseouljournal.com":"THESEOULJOURNALCOM"}
CONFIRM="QUARANTINE-LEGACY-NEWS"
CUTOFF="2026-08-21T00:00:00"

def req(method,site,path,pw,data=None,params=None):
    r=requests.request(method,f"https://{site}/wp-json/wp/v2/{path}",auth=(USER,pw),json=data,params=params,
      headers={"User-Agent":"WP-Newsroom-Quarantine/1.0"},timeout=40)
    if r.status_code>=400: raise RuntimeError(f"{site} {method} {path}: {r.status_code} {r.text[:400]}")
    return r.json() if r.text else {},r.headers

def quarantine(site):
    pw=os.getenv(ENV[site],"").strip()
    if not pw: raise RuntimeError(f"Missing {ENV[site]}")
    posts=[];page=1
    while True:
        batch,h=req("GET",site,"posts",pw,params={"status":"publish","before":CUTOFF,"per_page":100,"page":page,
          "_fields":"id,date,slug,link,title,status"})
        posts.extend(batch)
        if page>=int(h.get("X-WP-TotalPages","1")):break
        page+=1
    changed=[]
    for p in posts:
        saved,_=req("POST",site,f'posts/{p["id"]}',pw,{"status":"private"})
        changed.append({"id":p["id"],"date":p["date"],"slug":p["slug"],"link":p["link"],
          "title":p.get("title",{}).get("rendered",""),"before":"publish","after":saved.get("status")})
    return {"site":site,"cutoff":CUTOFF,"published_found":len(posts),"changed":changed,"deleted":0}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--site",choices=["ALL",*ENV],default="ALL");ap.add_argument("--confirm",required=True)
    ap.add_argument("--receipt",default="newsroom_legacy_quarantine_receipt.json");a=ap.parse_args()
    if a.confirm!=CONFIRM:raise SystemExit(f"Use --confirm {CONFIRM}")
    sites=list(ENV) if a.site=="ALL" else [a.site]
    out={"schema":1,"applied_at":datetime.now(timezone.utc).isoformat(),"results":[quarantine(s) for s in sites]}
    Path(a.receipt).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
