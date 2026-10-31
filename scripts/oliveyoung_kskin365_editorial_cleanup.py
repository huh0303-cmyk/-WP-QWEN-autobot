#!/usr/bin/env python3
"""Apply narrowly scoped title/image cleanup from the public audit manifest."""
import os,re,json,hashlib,argparse,html
from pathlib import Path
import requests
WP_USER="huh0303@gmail.com"
SITES={"oliveyoungkorea":{"url":"https://oliveyoungkorea.com","secret":"OLIVEYOUNGKOREACOM"},"kskin365":{"url":"https://kskin365.com","secret":"KSKIN365COM"}}
AUDIT_PATH="reports/oliveyoung-kskin365-editorial-audit-2026-11-01.json"
RETITLES={"kskin365":{2905:"Niacinamide 2%, 5%, and 10%: Choosing the Right Concentration for Korean Skincare"}}
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def fetch(s,b,pid):
 r=s.get(f"{b}/wp-json/wp/v2/posts/{pid}",params={"context":"edit"},timeout=35); r.raise_for_status(); return r.json()
def pat(url):
 e=re.escape(url).replace(r"\&",r"(?:&|&#038;|&amp;)")
 return re.compile(r"<figure\b[^>]*>(?:(?!</figure>).)*?<img\b[^>]*src=[\"'][^\"']*"+e+r"[^\"']*[\"'][^>]*>(?:(?!</figure>).)*?</figure>\s*|<p\b[^>]*>\s*<img\b[^>]*src=[\"'][^\"']*"+e+r"[^\"']*[\"'][^>]*>\s*</p>\s*|<img\b[^>]*src=[\"'][^\"']*"+e+r"[^\"']*[\"'][^>]*>",re.I|re.S)
def remove(content,url,keep_first=False):
 ms=list(pat(url).finditer(content)); rm=ms[1:] if keep_first else ms
 for m in reversed(rm): content=content[:m.start()]+content[m.end():]
 return content,len(rm)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); ap.add_argument("--out",default="reports/oliveyoung-kskin365-editorial-cleanup-2026-11-01.json"); a=ap.parse_args()
 audit=json.loads(Path(AUDIT_PATH).read_text(encoding="utf-8"))
 rep={"task":"oliveyoung-kskin365-editorial-cleanup","mode":"apply" if a.apply else "dry_run","sites":{}}
 for site,cfg in SITES.items():
  secret=os.getenv(cfg["secret"])
  if a.apply and not secret: raise SystemExit("Missing credential env var: "+cfg["secret"])
  s=requests.Session()
  if secret: s.auth=(WP_USER,secret)
  targets={}
  for group in audit[site]["cross_post_duplicate_image_groups"]:
   url=group["url"]
   ids=sorted({x["id"] for x in group["posts"]})
   for pid in ids[1:]: targets.setdefault(pid,[]).append(url)
  for item in audit[site]["within_post_duplicate_images"]:
   for url in item["repeated_urls"]: targets.setdefault(item["id"],[]).append(("KEEP_FIRST",url))
  changes=[]
  for pid in sorted(set(targets)|set(RETITLES.get(site,{}))):
   p=fetch(s,cfg["url"],pid)
   if p.get("status")!="publish": raise RuntimeError(f"{site} #{pid} is not published")
   co=p.get("content",{}); raw=co.get("raw") or ""; rendered=co.get("rendered") or ""
   to=p.get("title",{}); oldtitle=to.get("raw") or html.unescape(re.sub("<[^>]+>","",to.get("rendered","")))
   def apply_image_rules(source):
    result=source; removed_local=[]
    for spec in targets.get(pid,[]):
     if isinstance(spec,tuple): u=spec[1]; result,n=remove(result,u,True); rule="keep_first_within_post"
     else: u=spec; result,n=remove(result,u,False); rule="retain_lowest_post_id"
     if n: removed_local.append({"url":u,"blocks":n,"rule":rule})
    return result,removed_local
   raw_new,raw_removed=apply_image_rules(raw) if raw else (raw,[])
   rendered_new,rendered_removed=apply_image_rules(rendered) if rendered else (rendered,[])
   if len(rendered_removed)>len(raw_removed):
    old=rendered; new=rendered_new; removed=rendered_removed; content_source="rendered_fallback"
   else:
    old=raw or rendered; new=raw_new if raw else rendered_new; removed=raw_removed; content_source="raw" if raw else "rendered"
   newtitle=RETITLES.get(site,{}).get(pid,oldtitle)
   item={"post_id":pid,"link":p.get("link"),"title_before":oldtitle,"title_after":newtitle,"image_blocks_removed":removed,"content_source":content_source,"content_changed":new!=old,"title_changed":newtitle!=oldtitle}
   if a.apply and (new!=old or newtitle!=oldtitle):
    payload={}
    if new!=old: payload["content"]=new
    if newtitle!=oldtitle: payload["title"]=newtitle
    pr=s.post(f"{cfg['url']}/wp-json/wp/v2/posts/{pid}",json=payload,timeout=45); pr.raise_for_status()
    q=fetch(s,cfg["url"],pid); qc=q.get("content",{}); check=qc.get("raw") or qc.get("rendered") or ""
    qt=q.get("title",{}); checktitle=qt.get("raw") or html.unescape(re.sub("<[^>]+>","",qt.get("rendered","")))
    if content_source=="rendered_fallback":
     pub=requests.get(f"{cfg['url']}/wp-json/wp/v2/posts/{pid}",timeout=30); pub.raise_for_status()
     check=pub.json().get("content",{}).get("rendered","")
     images_still_present=[x["url"] for x in removed if x["url"] in check]
     if images_still_present: raise RuntimeError(f"Duplicate images remain {site} #{pid}: {images_still_present}")
    if checktitle!=newtitle or (new!=old and content_source!="rendered_fallback" and check!=new): raise RuntimeError(f"Readback mismatch {site} #{pid}")
    item.update({"status":"UPDATED_VERIFIED","sha256_before":sha(old),"sha256_after":sha(check),"updated_fields":list(payload)})
   elif a.apply: item["status"]="NO_CHANGE"
   changes.append(item)
  rep["sites"][site]={"target_posts":len(changes),"updated":sum(x.get("status")=="UPDATED_VERIFIED" for x in changes),"changes":changes}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"mode":rep["mode"],"sites":{k:{"target_posts":v["target_posts"],"updated":v["updated"],"planned":sum(x["content_changed"] or x["title_changed"] for x in v["changes"])} for k,v in rep["sites"].items()}},ensure_ascii=False))
if __name__=="__main__": main()
