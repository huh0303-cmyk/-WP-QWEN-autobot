#!/usr/bin/env python3
"""Insert or refresh the three-partner header banner on every published K-Health365 post."""
import os, re, json, time
from pathlib import Path
import requests, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation_hub.coupang_partners import render_header, HEADER_START, HEADER_END

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "huh0303@gmail.com").strip()
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
REPORT = Path("reports/khealth365-three-partner-banner-backfill.json")

def call(s, method, url, **kw):
    r=s.request(method,url,timeout=60,**kw)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
    return r

def main():
    if not PASSWORD:
        raise RuntimeError("KHEALTH365COM secret is empty")
    s=requests.Session()
    s.auth=(USER,PASSWORD)
    s.headers.update({"User-Agent":"KHealth365-Partner-Banner-Backfill/1.0"})
    me=call(s,"GET",SITE+"/wp-json/wp/v2/users/me",params={"context":"edit","_fields":"id"}).json()
    desired=render_header("wp_khealth365")
    for provider_url in (
        "https://www.trip.com/t/KwZ0AV4s0X2",
        "https://global.oliveyoung.com/if/rd?su=HUH556423",
        "https://link.coupang.com/a/ihRMHfQzKf",
    ):
        if provider_url not in desired:
            raise RuntimeError("Expected tracked partner URL missing from rendered header")
    report={"site":SITE,"wordpress_user_id":me.get("id"),"started_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "posts_found":0,"updated":0,"already_current":0,"errors":[],"results":[]}
    page=1
    while True:
        batch=call(s,"GET",SITE+"/wp-json/wp/v2/posts",params={
            "status":"publish","per_page":100,"page":page,"context":"edit",
            "_fields":"id,link,title,content,status"
        }).json()
        if not batch: break
        for post in batch:
            report["posts_found"]+=1
            pid=post["id"]
            raw=post.get("content",{}).get("raw")
            if raw is None:
                report["errors"].append({"id":pid,"reason":"raw content unavailable"}); continue
            # Remove any older managed header, then insert the canonical current banner.
            clean=re.sub(re.escape(HEADER_START)+r".*?"+re.escape(HEADER_END),"",raw,flags=re.S).lstrip()
            updated=desired+"\n"+clean
            if updated==raw:
                report["already_current"]+=1
                continue
            try:
                call(s,"POST",SITE+"/wp-json/wp/v2/posts/"+str(pid),json={"content":updated})
                check=call(s,"GET",SITE+"/wp-json/wp/v2/posts/"+str(pid),params={
                    "context":"edit","_fields":"id,link,content,status"
                }).json()
                saved=check.get("content",{}).get("raw","")
                if HEADER_START not in saved or HEADER_END not in saved or not all(u in saved for u in (
                    "https://www.trip.com/t/KwZ0AV4s0X2",
                    "https://global.oliveyoung.com/if/rd?su=HUH556423",
                    "https://link.coupang.com/a/ihRMHfQzKf"
                )):
                    raise RuntimeError("WordPress read-back verification failed")
                public=call(s,"GET",SITE+"/wp-json/wp/v2/posts/"+str(pid),params={"_fields":"id,link,content,status"}).json()
                rendered=public.get("content",{}).get("rendered","")
                if HEADER_START not in rendered or HEADER_END not in rendered:
                    raise RuntimeError("Public REST rendering is missing the banner")
                report["updated"]+=1
                report["results"].append({"id":pid,"url":post.get("link"),"status":"UPDATED_VERIFIED"})
            except Exception as exc:
                report["errors"].append({"id":pid,"reason":str(exc)[:400]})
        if len(batch)<100: break
        page+=1
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("posts_found","updated","already_current","errors")},ensure_ascii=False))
    if report["errors"]: raise SystemExit(2)

if __name__=="__main__":
    main()
