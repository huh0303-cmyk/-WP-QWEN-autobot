import json, re, html, hashlib, requests, time
from pathlib import Path
from collections import defaultdict, Counter
BASES = {"oliveyoungkorea":"https://oliveyoungkorea.com","kskin365":"https://kskin365.com"}
S=requests.Session(); S.headers["User-Agent"]="Mozilla/5.0 LondonProject editorial audit"
def plain(s): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s or ""))).strip()
def main():
 out={}
 for site,base in BASES.items():
  posts=[]; page=1
  while page<=20:
   r=S.get(base+"/wp-json/wp/v2/posts",params={"status":"publish","per_page":100,"page":page,"_fields":"id,date,modified,link,slug,title,content,featured_media"},timeout=30)
   r.raise_for_status()
   rows=r.json()
   if not rows: break
   for p in rows:
    body=p.get("content",{}).get("rendered","")
    imgs=re.findall(r'<img\b[^>]*?\bsrc=["\']([^"\']+)',body,re.I)
    title=plain(p.get("title",{}).get("rendered",""))
    posts.append({"id":p["id"],"title":title,"link":p["link"],"modified":p["modified"],"featured_media":p.get("featured_media",0),"images":imgs,"content":body})
   if len(rows)<100: break
   page+=1
  titlemap=defaultdict(list); imagemap=defaultdict(list)
  for p in posts:
   norm=re.sub(r"[^a-z0-9]+"," ",p["title"].lower()).strip()
   titlemap[norm].append({"id":p["id"],"title":p["title"],"link":p["link"]})
   for u in p["images"]:
    imagemap[u].append({"id":p["id"],"title":p["title"],"link":p["link"]})
  dup_titles=[v for k,v in titlemap.items() if k and len(v)>1]
  dup_images=[{"url":u,"posts":v} for u,v in imagemap.items() if len(v)>1]
  within=[]
  for p in posts:
   c=Counter(p["images"])
   repeated=[u for u,n in c.items() if n>1]
   if repeated: within.append({"id":p["id"],"title":p["title"],"link":p["link"],"repeated_urls":repeated})
  out[site]={"base":base,"published_count":len(posts),"duplicate_title_groups":dup_titles,"cross_post_duplicate_image_groups":dup_images,"within_post_duplicate_images":within,"posts":[{k:v for k,v in p.items() if k!="content"} for p in posts]}
  print(json.dumps({"site":site,"published":len(posts),"duplicate_title_groups":len(dup_titles),"cross_post_duplicate_image_groups":len(dup_images),"within_post_duplicate_images":len(within)},ensure_ascii=False),flush=True)
 Path("reports").mkdir(exist_ok=True)
 Path("reports/oliveyoung-kskin365-editorial-audit-2026-11-01.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
