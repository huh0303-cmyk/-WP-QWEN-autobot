#!/usr/bin/env python3
"""Safe unindexed-post pruner for the WordPress blog network.

Invariant:
- NO domain may be force-reset or hidden by domain name.
- Every published post is checked individually with Google Search Console URL Inspection.
- Only a successful inspection with verdict != PASS may become private.
- PASS stays public.
- API/quota/permission/network uncertainty stays public.
- News sites are excluded from this blog-pruning workflow.
- Never deletes posts.
"""
import json, os, socket, sys, time
import requests

_original_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import ACTIVE_SITES  # noqa: E402
from daily_site_traffic import get_gsc_token, gsc_get  # noqa: E402

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
RESULTS_PATH = "prune_unindexed_result.json"
NEWS_DOMAINS = {"koreanews365.com", "theseouljournal.com"}
UA = {"User-Agent": "Mozilla/5.0 (GitHubActions; WP-GSC-Safe-Pruner/2.0)"}

def save(data):
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_posts(site_url):
    out=[]; page=1
    while True:
        r=requests.get(f"{site_url}/wp-json/wp/v2/posts",
            params={"status":"publish","per_page":100,"page":page,"_fields":"id,link,title"},
            headers=UA,timeout=35)
        if r.status_code==400 and "rest_post_invalid_page_number" in r.text: break
        if r.status_code!=200: raise RuntimeError(f"posts HTTP {r.status_code}: {r.text[:180]}")
        batch=r.json()
        if not batch: break
        out.extend(batch)
        if len(batch)<100: break
        page+=1
    return out

def title_of(post):
    t=post.get("title") or ""
    return t.get("rendered","") if isinstance(t,dict) else str(t)

def property_for(domain, site_url, accessible):
    for p in (site_url.rstrip("/")+"/", f"sc-domain:{domain}", site_url.rstrip("/")):
        if p in accessible: return p
    return None

def inspect_url(token, prop, url, retries=3):
    for attempt in range(retries):
        r=requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
            json={"inspectionUrl":url,"siteUrl":prop},timeout=30)
        if r.status_code==200:
            s=r.json().get("inspectionResult",{}).get("indexStatusResult",{})
            return {"ok":True,"verdict":s.get("verdict"),"coverageState":s.get("coverageState"),
                    "indexingState":s.get("indexingState"),"lastCrawlTime":s.get("lastCrawlTime")}
        if r.status_code==429:
            time.sleep(5*(attempt+1)); continue
        return {"ok":False,"error":f"HTTP {r.status_code}: {r.text[:180]}"}
    return {"ok":False,"error":"429 retry exhausted"}

def set_private(site_url,pw,post_id):
    r=requests.post(f"{site_url}/wp-json/wp/v2/posts/{post_id}",auth=(WP_USER,pw),
        json={"status":"private"},headers=UA,timeout=35)
    return r.status_code in (200,201),r.status_code,r.text[:180]

def main():
    token=get_gsc_token(); resp=gsc_get(token,"/sites")
    if resp.status_code!=200: raise RuntimeError(f"GSC sites HTTP {resp.status_code}: {resp.text[:180]}")
    accessible={x.get("siteUrl") for x in resp.json().get("siteEntry",[]) if x.get("siteUrl")}
    results={}
    targets=[row for row in ACTIVE_SITES if row[0].replace("https://","").rstrip("/") not in NEWS_DOMAINS]
    print(f"Safe GSC-only pruning targets={len(targets)}",flush=True)
    for site_url,env_key,lifecycle in targets:
        site_url=site_url.rstrip("/"); domain=site_url.replace("https://","")
        pw=os.getenv(env_key,"").strip()
        if not pw:
            results[domain]={"status":"SKIP_NO_SECRET","secret":env_key}; save(results); continue
        prop=property_for(domain,site_url,accessible)
        if not prop:
            results[domain]={"status":"SKIP_NO_GSC_PROPERTY"}; save(results); continue
        try: posts=fetch_posts(site_url)
        except Exception as e:
            results[domain]={"status":"FETCH_FAILED","error":str(e)}; save(results); continue
        row={"status":"OK","mode":"GSC_URL_INSPECTION_ONLY","gsc_property":prop,
             "total_public_before":len(posts),"indexed_kept":0,"made_private":0,
             "inspection_uncertain_kept":0,"private_failed":0,"items":[]}
        for p in posts:
            ins=inspect_url(token,prop,p.get("link")); item={"id":p["id"],"url":p.get("link"),"title":title_of(p),"inspection":ins}
            if not ins.get("ok"):
                item["decision"]="KEEP_UNCERTAIN"; row["inspection_uncertain_kept"]+=1
            elif ins.get("verdict")=="PASS":
                item["decision"]="KEEP_INDEXED"; row["indexed_kept"]+=1
            else:
                ok,code,detail=set_private(site_url,pw,p["id"])
                if ok:
                    item["decision"]="PRIVATE_CONFIRMED_UNINDEXED"; row["made_private"]+=1
                else:
                    item["decision"]="PRIVATE_FAILED"; item["http"]=code; item["error"]=detail; row["private_failed"]+=1
            row["items"].append(item); results[domain]=row; save(results); time.sleep(1.05)
        results[domain]=row; save(results)
    results["_TOTALS"]={
        "sites_processed":sum(1 for x in results.values() if isinstance(x,dict) and x.get("status")=="OK"),
        "indexed_kept":sum(x.get("indexed_kept",0) for x in results.values() if isinstance(x,dict)),
        "made_private":sum(x.get("made_private",0) for x in results.values() if isinstance(x,dict)),
        "uncertain_kept":sum(x.get("inspection_uncertain_kept",0) for x in results.values() if isinstance(x,dict)),
        "private_failed":sum(x.get("private_failed",0) for x in results.values() if isinstance(x,dict)),
    }; save(results)
    print(json.dumps(results["_TOTALS"],ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__": main()
