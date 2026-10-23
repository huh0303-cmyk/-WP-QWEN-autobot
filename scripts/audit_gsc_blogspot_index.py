#!/usr/bin/env python3
"""Read-only GSC/Blogspot inventory for all published posts.

Clone of scripts/audit_gsc_post_index.py for the 33 Blogspot properties.
Reuses the exact same GSC auth/inspection logic; the only real difference is
how the list of published post URLs is collected - Blogger's public Atom
feed instead of the WordPress REST API, which conveniently needs no
authentication at all.

Never treats API errors, missing permissions, or quota failures as unindexed.
Writes a resumable evidence manifest; it does not modify any Blogspot blog.
"""
import argparse, datetime as dt, json, os, re, time
from pathlib import Path
import requests
from blogspot_site_registry import BLOGSPOT_SITES

OUT = Path(os.getenv("INDEX_AUDIT_OUT", "blogspot_index_audit_manifest.json"))
GSC_JSON = os.getenv("GSC_SERVICE_ACCOUNT_JSON", "")
_TOKEN_CACHE = {"value": "", "until": 0}

def token(force=False):
    if not force and _TOKEN_CACHE["value"] and time.time() < _TOKEN_CACHE["until"]:
        return _TOKEN_CACHE["value"]
    import jwt
    key=json.loads(GSC_JSON); now=int(time.time())
    assertion=jwt.encode({"iss":key["client_email"],"scope":"https://www.googleapis.com/auth/webmasters.readonly",
        "aud":"https://oauth2.googleapis.com/token","iat":now,"exp":now+3600},key["private_key"],algorithm="RS256")
    r=requests.post("https://oauth2.googleapis.com/token",data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":assertion},timeout=20)
    r.raise_for_status()
    payload = r.json()
    _TOKEN_CACHE.update(value=payload["access_token"], until=time.time() + int(payload.get("expires_in", 3600)) - 120)
    return _TOKEN_CACHE["value"]

def properties(tok):
    r=requests.get("https://www.googleapis.com/webmasters/v3/sites",headers={"Authorization":f"Bearer {tok}"},timeout=20)
    r.raise_for_status(); return {x["siteUrl"] for x in r.json().get("siteEntry",[])}

def property_for(site, props):
    domain=site.removeprefix("https://").rstrip("/")
    for p in (site.rstrip("/")+"/", site.rstrip("/"), f"sc-domain:{domain}"):
        if p in props: return p
    return None

_POST_ID_RE = re.compile(r"post-(\d+)$")

def posts(blog_id):
    """Fetch every published post via Blogger's public feed (no auth needed).

    A blog set to private/unlisted would fail here with a non-200 - treated
    like any other fetch failure below (recorded as an error, never silently
    read as zero posts).
    """
    out=[]; start=1; per_page=150
    while True:
        r=requests.get(
            f"https://www.blogger.com/feeds/{blog_id}/posts/default",
            params={"alt":"json","max-results":per_page,"start-index":start,"orderby":"published"},
            timeout=30,
        )
        r.raise_for_status()
        entries = r.json().get("feed", {}).get("entry", [])
        if not entries: break
        for e in entries:
            alt = next((l["href"] for l in e.get("link", []) if l.get("rel")=="alternate"), None)
            if not alt: continue
            match = _POST_ID_RE.search(e["id"]["$t"])
            post_id = match.group(1) if match else e["id"]["$t"]
            out.append({
                "id": post_id, "link": alt, "title": e.get("title", {}).get("$t", ""),
                "date_gmt": e["published"]["$t"], "modified_gmt": e["updated"]["$t"],
            })
        if len(entries) < per_page: break
        start += per_page
    return out

def inspect(tok, prop, url):
    for attempt in range(2):
        r=requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},
            json={"inspectionUrl":url,"siteUrl":prop},timeout=30)
        if r.status_code != 401 or attempt:
            break
        tok = token(force=True)
    if r.status_code!=200:
        return {"state":"unknown","http":r.status_code,"error":r.text[:300]}
    s=r.json().get("inspectionResult",{}).get("indexStatusResult",{})
    verdict=s.get("verdict")
    return {"state":"indexed" if verdict=="PASS" else "unindexed" if verdict in ("FAIL", "NEUTRAL") else "unknown","verdict":verdict,
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
    ap.add_argument("--sleep",type=float,default=.35); ap.add_argument("--refresh-all",action="store_true"); ap.add_argument("--retry-unknown",action="store_true"); args=ap.parse_args()
    if not GSC_JSON: raise SystemExit("GSC_SERVICE_ACCOUNT_JSON missing")
    tok=token(); props=properties(tok); manifest=load()
    today=dt.datetime.now(dt.timezone.utc)
    for site, blog_id, lifecycle in BLOGSPOT_SITES:
        if args.site and args.site not in site: continue
        prop=property_for(site,props)
        entry=manifest["sites"].setdefault(site,{"lifecycle":lifecycle,"blog_id":blog_id,"property":prop,"posts":{}})
        previous_summary=dict(entry.get("summary") or {})
        entry["property"]=prop
        if not prop:
            entry["error"]="gsc_property_not_accessible"; save(manifest); continue
        try: items=posts(blog_id)
        except Exception as e:
            entry["error"]=f"blogspot_feed_failed: {e}"; save(manifest); continue
        if args.max_per_site: items=items[:args.max_per_site]
        active_ids={p["id"] for p in items}
        for stale_id in set(entry["posts"]) - active_ids:
            entry["posts"].pop(stale_id, None)
        for i,p in enumerate(items,1):
            key=p["id"]; old=entry["posts"].get(key,{})
            if (args.retry_unknown or not args.refresh_all) and old.get("state") in ("indexed","unindexed"): continue
            tok = token()
            try:
                result=inspect(tok,prop,p["link"])
            except requests.RequestException:
                result={"state":"unknown", "error":"inspection_network_error"}
            result["checked_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            published=dt.datetime.fromisoformat(p["date_gmt"])
            if published.tzinfo is None:
                published=published.replace(tzinfo=dt.timezone.utc)
            age=(today-published).days
            result.update({"id":p["id"],"url":p["link"],"title":p["title"],
                "published_gmt":p["date_gmt"],"modified_gmt":p["modified_gmt"],"age_days":age,
                "private_candidate":result["state"]=="unindexed" and age>=60})
            entry["posts"][key]=result
            if i%10==0: save(manifest)
            time.sleep(args.sleep)
        states=[x.get("state") for x in entry["posts"].values()]
        summary={k:states.count(k) for k in ("indexed","unindexed","unknown")}
        old_indexed=previous_summary.get("indexed")
        summary["indexed_delta"]=None if old_indexed is None or summary["unknown"] or previous_summary.get("unknown") else summary["indexed"]-int(old_indexed)
        summary["total_published"]=len(entry["posts"])
        summary["complete"] = summary["unknown"] == 0
        summary["comparison_at"] = entry.get("audited_at") if summary["indexed_delta"] is not None else None
        entry["summary"]=summary
        entry["audited_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
        entry.pop("error", None)
        save(manifest)
    print(json.dumps({s:v.get("summary",{}) for s,v in manifest["sites"].items()},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
