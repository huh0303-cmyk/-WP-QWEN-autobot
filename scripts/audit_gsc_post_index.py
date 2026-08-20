#!/usr/bin/env python3
"""Read-only GSC/WordPress inventory for all published posts.

Never treats API errors, missing permissions, or quota failures as unindexed.
Writes a resumable evidence manifest; it does not modify WordPress.
"""
import argparse, datetime as dt, json, os, time
from pathlib import Path
import requests
from site_registry import SITES

OUT = Path(os.getenv("INDEX_AUDIT_OUT", "index_audit_manifest.json"))
GSC_JSON = os.getenv("GSC_SERVICE_ACCOUNT_JSON", "")

def token():
    import jwt
    key=json.loads(GSC_JSON); now=int(time.time())
    assertion=jwt.encode({"iss":key["client_email"],"scope":"https://www.googleapis.com/auth/webmasters.readonly",
        "aud":"https://oauth2.googleapis.com/token","iat":now,"exp":now+3600},key["private_key"],algorithm="RS256")
    r=requests.post("https://oauth2.googleapis.com/token",data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":assertion},timeout=20)
    r.raise_for_status(); return r.json()["access_token"]

def properties(tok):
    r=requests.get("https://www.googleapis.com/webmasters/v3/sites",headers={"Authorization":f"Bearer {tok}"},timeout=20)
    r.raise_for_status(); return {x["siteUrl"] for x in r.json().get("siteEntry",[])}

def property_for(site, props):
    domain=site.removeprefix("https://").rstrip("/")
    for p in (site.rstrip("/")+"/", site.rstrip("/"), f"sc-domain:{domain}"):
        if p in props: return p
    return None

def posts(site):
    out=[]; page=1
    while True:
        r=requests.get(f"{site}/wp-json/wp/v2/posts",params={"status":"publish","per_page":100,"page":page,
            "orderby":"date","order":"asc","_fields":"id,link,slug,date_gmt,modified_gmt,title"},timeout=30)
        if r.status_code==400 and "rest_post_invalid_page_number" in r.text: break
        r.raise_for_status(); batch=r.json()
        if not batch: break
        out.extend(batch)
        if len(batch)<100: break
        page+=1
    return out

def inspect(tok, prop, url):
    r=requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},
        json={"inspectionUrl":url,"siteUrl":prop},timeout=30)
    if r.status_code!=200:
        return {"state":"unknown","http":r.status_code,"error":r.text[:300]}
    s=r.json().get("inspectionResult",{}).get("indexStatusResult",{})
    verdict=s.get("verdict")
    return {"state":"indexed" if verdict=="PASS" else "unindexed","verdict":verdict,
        "coverageState":s.get("coverageState"),"robotsTxtState":s.get("robotsTxtState"),
        "indexingState":s.get("indexingState"),"lastCrawlTime":s.get("lastCrawlTime"),
        "googleCanonical":s.get("googleCanonical"),"userCanonical":s.get("userCanonical"),
        "pageFetchState":s.get("pageFetchState")}

def load():
    if OUT.exists():
        try:return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:pass
    return {"schema":1,"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"sites":{}}

def save(m):
    m["updated_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--site"); ap.add_argument("--max-per-site",type=int,default=0)
    ap.add_argument("--sleep",type=float,default=.35); args=ap.parse_args()
    if not GSC_JSON: raise SystemExit("GSC_SERVICE_ACCOUNT_JSON missing")
    tok=token(); props=properties(tok); manifest=load()
    today=dt.datetime.now(dt.timezone.utc)
    for site, secret, lifecycle in SITES:
        if args.site and args.site not in site: continue
        prop=property_for(site,props)
        entry=manifest["sites"].setdefault(site,{"lifecycle":lifecycle,"property":prop,"posts":{}})
        entry["property"]=prop
        if not prop:
            entry["error"]="gsc_property_not_accessible"; save(manifest); continue
        try: items=posts(site)
        except Exception as e:
            entry["error"]=f"wp_inventory_failed: {e}"; save(manifest); continue
        if args.max_per_site: items=items[:args.max_per_site]
        for i,p in enumerate(items,1):
            key=str(p["id"]); old=entry["posts"].get(key,{})
            if old.get("state") in ("indexed","unindexed"): continue
            result=inspect(tok,prop,p["link"])
            published=dt.datetime.fromisoformat(p["date_gmt"].replace("Z","+00:00"))
            age=(today-published).days
            result.update({"id":p["id"],"url":p["link"],"slug":p["slug"],"title":p["title"]["rendered"],
                "published_gmt":p["date_gmt"],"modified_gmt":p["modified_gmt"],"age_days":age,
                "private_candidate":result["state"]=="unindexed" and age>=60})
            entry["posts"][key]=result
            if i%10==0: save(manifest)
            time.sleep(args.sleep)
        states=[x.get("state") for x in entry["posts"].values()]
        entry["summary"]={k:states.count(k) for k in ("indexed","unindexed","unknown")}
        save(manifest)
    print(json.dumps({s:v.get("summary",{}) for s,v in manifest["sites"].items()},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
