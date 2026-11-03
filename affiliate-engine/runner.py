#!/usr/bin/env python3
"""Append verified, per-destination affiliate offers to WordPress and Blogger."""
from __future__ import annotations
import argparse, hashlib, html, json, os, sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT/"affiliate-engine"
ROUTING=ENGINE/"config"/"affiliate-routing.json"
POLICY=ROOT/"config"/"affiliate_distribution_policy.json"
CATALOG_DIR=ENGINE/"data"/"catalogs"
MARKER="<!-- london-affiliate-engine:v3 -->"
DISCLOSURE="<p><small>Disclosure: This section contains affiliate links. We may earn a commission at no extra cost to you.</small></p>"

def load_json(path:Path)->Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def normalized(value:str)->str:
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in value).split())

def recent_since(hours:int)->str:
    return (datetime.now(UTC)-timedelta(hours=hours)).isoformat().replace("+00:00","Z")

def load_destinations(platform:str)->list[dict[str,str]]:
    profiles=load_json(ROOT/"config"/"content_engine_profiles.json")["profiles"]
    seen=set(); out=[]
    for profile in profiles:
        target=profile.get(platform,{})
        key=str(target.get("url") or target.get("destination_id") or "").strip()
        if not key or key in seen or not target.get("ready_for_automation",True): continue
        seen.add(key)
        out.append({"site_key":str(profile["site_key"]),"url":str(target.get("url","")),"secret_name":str(target.get("secret_name","")),"destination_id":str(target.get("destination_id",""))})
    return out

def load_site_offers(site_key:str)->list[dict[str,Any]]:
    path=CATALOG_DIR/f"{site_key}.json"
    if not path.exists(): raise ValueError(f"missing_site_catalog:{site_key}")
    payload=load_json(path)
    if payload.get("status") not in {"verified","ready"}: raise ValueError(f"catalog_not_verified:{site_key}")
    return payload.get("offers",[])

def select_offers(title:str,content:str,routing:dict[str,Any],site_key:str,offers:list[dict[str,Any]]|None=None)->list[dict[str,Any]]:
    offers=offers if offers is not None else load_site_offers(site_key)
    body=normalized(f"{title} {content}")
    chosen=[]
    for slot in routing["required_slots"]:
        provider=slot["provider"]
        candidates=[o for o in offers if o.get("slot")==slot["slot"] and o.get("provider")==provider]
        candidates=[o for o in candidates if o.get("affiliate_link_verified") is True and o.get("image_rights_verified") is True and all(urlparse(str(o.get(k,""))).scheme=="https" and urlparse(str(o.get(k,""))).netloc for k in ("url","image_url"))]
        if slot["slot"].startswith("coupang_topic_"):
            candidates=[o for o in candidates if any(normalized(k) in body for k in o.get("keywords",[]) if k)]
        if not candidates: raise ValueError(f"missing_verified_offer:{slot['slot']}:{provider}")
        candidates.sort(key=lambda o:hashlib.sha256(f"{title}:{slot['slot']}:{o['url']}".encode()).hexdigest())
        chosen.append(candidates[0])
    if len(chosen)!=10: raise ValueError(f"expected_10_offers_got_{len(chosen)}")
    if len({o["url"] for o in chosen})!=10: raise ValueError("duplicate_tracking_url_in_selected_offers")
    counts={}
    for o in chosen: counts[o["provider"]]=counts.get(o["provider"],0)+1
    expected={"coupang_partners":4,"olive_young_global":2,"trip_com":2,"agoda":2}
    if counts!=expected: raise ValueError(f"provider_mix_mismatch:{counts}")
    return chosen

def build_block(offers:list[dict[str,Any]])->str:
    cards=[]
    for o in offers:
        cards.append("<article class=\"london-affiliate-card\"><a href=\"%s\" rel=\"sponsored nofollow noopener\" target=\"_blank\"><img src=\"%s\" alt=\"%s\" loading=\"lazy\"/><strong>%s</strong><span>쇼핑하기</span></a></article>"%(html.escape(o["url"],quote=True),html.escape(o["image_url"],quote=True),html.escape(o.get("image_alt",o["title"]),quote=True),html.escape(o["title"])))
    css="<style>.london-affiliate-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.london-affiliate-card img{width:100%;aspect-ratio:1/1;object-fit:cover}.london-affiliate-card a{display:flex;flex-direction:column;gap:8px;text-decoration:none}.london-affiliate-card span{font-weight:700}@media(max-width:640px){.london-affiliate-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>"
    return "\n".join([MARKER,"<section class=\"london-affiliate-engine\"><h2>Recommended products and travel offers</h2>",DISCLOSURE,css,"<div class=\"london-affiliate-grid\">",*cards,"</div></section>"])

def can_write(requested:bool)->bool:
    return requested and os.getenv("AFFILIATE_WRITE_ENABLED","").lower()=="true"

def wordpress(dest,since,block_for,write,scope,batch_size):
    base=dest["url"].rstrip("/"); password=os.getenv(dest["secret_name"],""); rows=[]; page=1
    while len(rows)<batch_size:
        params={"status":"publish","per_page":100,"page":page,"orderby":"date","order":"desc"}
        if scope=="new": params["after"]=since
        response=requests.get(f"{base}/wp-json/wp/v2/posts",params=params,timeout=30)
        if response.status_code==400 and page>1: break
        response.raise_for_status(); posts=response.json()
        if not posts: break
        for post in posts:
            content=post["content"]["rendered"]
            result={"platform":"wordpress","site":dest["site_key"],"post_id":post["id"],"url":post["link"],"action":"skipped"}
            if MARKER in content: result["reason"]="already_has_v3_marker"
            else:
                try: block=block_for(post["title"]["rendered"],content,dest["site_key"])
                except ValueError as exc: result.update(action="blocked",reason=str(exc))
                else:
                    result["action"]="would_append"
                    if write:
                        if not password: result.update(action="blocked",reason="missing_wordpress_secret")
                        else:
                            update=requests.post(f"{base}/wp-json/wp/v2/posts/{post['id']}",auth=(os.getenv("WP_USER",""),password),json={"content":content+"\n"+block},timeout=30)
                            update.raise_for_status()
                            verify=requests.get(f"{base}/wp-json/wp/v2/posts/{post['id']}",params={"context":"edit"},auth=(os.getenv("WP_USER",""),password),timeout=30)
                            verify.raise_for_status()
                            if MARKER not in verify.json()["content"]["raw"]: raise RuntimeError("wordpress_readback_marker_missing")
                            result["action"]="appended_verified"
            rows.append(result)
            if len(rows)>=batch_size: break
        if scope=="new" or len(posts)<100: break
        page+=1
    return rows

def blogger_token():
    response=requests.post("https://oauth2.googleapis.com/token",data={"client_id":os.getenv("BLOGGER_GOOGLE_CLIENT_ID",""),"client_secret":os.getenv("BLOGGER_GOOGLE_CLIENT_SECRET",""),"refresh_token":os.getenv("BLOGGER_GOOGLE_REFRESH_TOKEN",""),"grant_type":"refresh_token"},timeout=30)
    response.raise_for_status(); return response.json()["access_token"]

def blogger(dest,since,block_for,write,scope,batch_size):
    if not dest["destination_id"]: return []
    token=blogger_token() if write else ""; headers={"Authorization":f"Bearer {token}"} if token else {}
    endpoint=f"https://www.googleapis.com/blogger/v3/blogs/{dest['destination_id']}/posts"; rows=[]; page_token=""
    while len(rows)<batch_size:
        params={"fetchBodies":"true","maxResults":100}
        if scope=="new": params["publishedMin"]=since
        if page_token: params["pageToken"]=page_token
        response=requests.get(endpoint,params=params,headers=headers,timeout=30); response.raise_for_status(); payload=response.json()
        for post in payload.get("items",[]):
            content=post["content"]; result={"platform":"blogger","site":dest["site_key"],"post_id":post["id"],"url":post["url"],"action":"skipped"}
            if MARKER in content: result["reason"]="already_has_v3_marker"
            else:
                try: block=block_for(post["title"],content,dest["site_key"])
                except ValueError as exc: result.update(action="blocked",reason=str(exc))
                else:
                    result["action"]="would_append"
                    if write:
                        update=requests.put(f"{endpoint}/{post['id']}",headers=headers,json={"title":post["title"],"content":content+"\n"+block},timeout=30)
                        update.raise_for_status()
                        verify=requests.get(f"{endpoint}/{post['id']}",params={"fetchBody":"true"},headers=headers,timeout=30); verify.raise_for_status()
                        if MARKER not in verify.json().get("content",""): raise RuntimeError("blogger_readback_marker_missing")
                        result["action"]="appended_verified"
            rows.append(result)
            if len(rows)>=batch_size: break
        page_token=payload.get("nextPageToken","")
        if scope=="new" or not page_token: break
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--platform",choices=["wordpress","blogger","all"],default="all")
    parser.add_argument("--scope",choices=["new","backfill"],default="new")
    parser.add_argument("--since-hours",type=int,default=36)
    parser.add_argument("--batch-size",type=int,default=5)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args(); routing=load_json(ROUTING); write=can_write(args.write)
    if args.write and not write: raise SystemExit("write blocked: set AFFILIATE_WRITE_ENABLED=true as a GitHub secret")
    since=recent_since(args.since_hours)
    def block_for(title,content,site_key): return build_block(select_offers(title,content,routing,site_key))
    results=[]
    if args.platform in {"wordpress","all"}:
        for dest in load_destinations("wordpress"):
            try: results.extend(wordpress(dest,since,block_for,write,args.scope,args.batch_size))
            except (requests.RequestException,ValueError,RuntimeError) as exc: results.append({"platform":"wordpress","site":dest["site_key"],"action":"blocked","reason":str(exc)[:240]})
    if args.platform in {"blogger","all"}:
        for dest in load_destinations("blogger"):
            try: results.extend(blogger(dest,since,block_for,write,args.scope,args.batch_size))
            except (requests.RequestException,ValueError,RuntimeError) as exc: results.append({"platform":"blogger","site":dest["site_key"],"action":"blocked","reason":str(exc)[:240]})
    report={"generated_at":datetime.now(UTC).isoformat(),"scope":args.scope,"since":since,"batch_size":args.batch_size,"write":write,"policy":"4+2+2+2","results":results}
    out=ENGINE/"reports"/f"latest-{args.scope}-run.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"write":write,"processed":len(results),"appended_verified":sum(r["action"]=="appended_verified" for r in results),"blocked":sum(r["action"]=="blocked" for r in results)},ensure_ascii=False))
    return 0
if __name__=="__main__": sys.exit(main())
