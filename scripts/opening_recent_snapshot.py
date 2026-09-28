#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/opening_recent_snapshot.json"
UA={"User-Agent":"Mozilla/5.0 Korea365-Control/1.0"}

def d(v):
    if not v: return ""
    s=str(v)
    if s.isdigit():
        n=int(s)
        if n>10_000_000_000: n//=1000
        if n>1_000_000_000:
            return datetime.fromtimestamp(n,timezone.utc).date().isoformat()
    try:return datetime.fromisoformat(s.replace("Z","+00:00")).date().isoformat()
    except Exception:
        m=re.search(r"(20\d{2}|19\d{2})[-/.](\d{1,2})[-/.](\d{1,2})",s)
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""

def wp_dates(url):
    try:
        latest=requests.get(url.rstrip("/")+"/wp-json/wp/v2/posts",params={"status":"publish","per_page":1,"orderby":"date","order":"desc","_fields":"date"},headers=UA,timeout=15);latest.raise_for_status()
        oldest=requests.get(url.rstrip("/")+"/wp-json/wp/v2/posts",params={"status":"publish","per_page":1,"orderby":"date","order":"asc","_fields":"date"},headers=UA,timeout=15);oldest.raise_for_status()
        l=latest.json();o=oldest.json()
        return d(o[0]["date"]) if o else "", d(l[0]["date"]) if l else ""
    except Exception:return "",""

def blogger_dates(url):
    try:
        r=requests.get(url.rstrip("/")+"/feeds/posts/default",params={"alt":"json","max-results":500},headers=UA,timeout=20);r.raise_for_status()
        entries=r.json().get("feed",{}).get("entry",[])
        dates=[d(x.get("published",{}).get("$t")) for x in entries]
        dates=[x for x in dates if x]
        return (min(dates),max(dates)) if dates else ("","")
    except Exception:return "",""

def tistory_dates(url):
    try:
        r=requests.get(url.rstrip("/")+"/rss",headers=UA,timeout=15);r.raise_for_status()
        root=ET.fromstring(r.content)
        vals=[]
        for item in root.findall("./channel/item"):
            t=item.findtext("pubDate")
            if t:
                try: vals.append(datetime.strptime(t,"%a, %d %b %Y %H:%M:%S %z").date().isoformat())
                except Exception: pass
        return (min(vals),max(vals)) if vals else ("","")
    except Exception:return "",""

def naver_dates(blog_id):
    dates=[]; seen=set()
    headers={**UA,"Referer":f"https://m.blog.naver.com/{blog_id}","Accept":"application/json, text/plain, */*","X-Requested-With":"XMLHttpRequest"}
    for page in range(1,21):
        try:
            r=requests.get(f"https://m.blog.naver.com/api/blogs/{blog_id}/post-list",params={"categoryNo":0,"itemCount":30,"page":page},headers=headers,timeout=15);r.raise_for_status()
            items=r.json().get("result",{}).get("items",[])
        except Exception: break
        if not items: break
        added=0
        for item in items:
            log=str(item.get("logNo") or "")
            if not log or log in seen: continue
            seen.add(log);added+=1
            dt=d(item.get("addDate"))
            if dt:dates.append(dt)
        if not added: break
        time.sleep(.05)
    return (min(dates),max(dates)) if dates else ("","")

def youtube_rows(items):
    key=os.getenv("YOUTUBE_API_KEY","")
    created={}
    if key and items:
        ids=",".join(x["channel_id"] for x in items if x.get("channel_id"))
        try:
            r=requests.get("https://www.googleapis.com/youtube/v3/channels",params={"part":"snippet","id":ids,"key":key},timeout=20);r.raise_for_status()
            for x in r.json().get("items",[]):created[x["id"]]=d(x.get("snippet",{}).get("publishedAt"))
        except Exception:pass
    out={}
    ns={"a":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
    for x in items:
        cid=x.get("channel_id",""); recent=""
        try:
            r=requests.get("https://www.youtube.com/feeds/videos.xml",params={"channel_id":cid},headers=UA,timeout=12);r.raise_for_status()
            root=ET.fromstring(r.content); vals=[d(e.findtext("a:published",default="",namespaces=ns)) for e in root.findall("a:entry",ns)]; vals=[v for v in vals if v]
            recent=max(vals) if vals else ""
        except Exception:pass
        out[cid]={"opening_date":created.get(cid,""),"recent_publish_date":recent}
    return out

def main():
    import concurrent.futures
    profiles=json.loads((ROOT/"config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    tistory=json.loads((ROOT/"config/tistory_portfolio.json").read_text(encoding="utf-8"))["sites"]
    rooms=json.loads((ROOT/"config/automation_rooms.json").read_text(encoding="utf-8"))["rooms"]
    inv=json.loads((ROOT/"config/london_social_account_inventory_2026-09-24.json").read_text(encoding="utf-8"))
    jobs=[]
    for p in profiles:
        u=(p.get("wordpress") or {}).get("url")
        if u: jobs.append(("blog",u.rstrip("/"),wp_dates,u.rstrip("/")))
        u=(p.get("blogspot") or {}).get("url")
        if u: jobs.append(("blog",u.rstrip("/"),blogger_dates,u.rstrip("/")))
    for x in tistory:
        u=x["url"].rstrip("/");jobs.append(("blog",u,tistory_dates,u))
    for x in rooms:
        if x.get("platform")=="naver":
            bid=x.get("destination_id","");jobs.append(("naver",f"https://blog.naver.com/{bid}",naver_dates,bid))
    def run(job):
        kind,key,fn,arg=job
        try: op,rc=fn(arg)
        except Exception: op,rc="",""
        return key,{"opening_date":op,"recent_publish_date":rc}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        blogs=dict(ex.map(run,jobs))
    payload={"generated_at":datetime.now(timezone.utc).isoformat(),"blogs":blogs,"youtube":youtube_rows(inv.get("youtube",[])),"social":{}}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"blogs":len(blogs),"youtube":len(payload["youtube"]),"blog_opening":sum(bool(x["opening_date"]) for x in blogs.values()),"blog_recent":sum(bool(x["recent_publish_date"]) for x in blogs.values()),"yt_opening":sum(bool(x["opening_date"]) for x in payload["youtube"].values()),"yt_recent":sum(bool(x["recent_publish_date"]) for x in payload["youtube"].values())},ensure_ascii=False))

if __name__=="__main__":main()
