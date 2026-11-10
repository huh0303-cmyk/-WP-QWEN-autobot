"""Apply weekly SeoulMall + 10 Coupang cards to all published Kworld365 posts."""
import json,os,requests
from pathlib import Path
from scripts.kworld_weekly_affiliate_footer import replace,MARKER
SITE="https://kworld365.com"
AUTH=("huh0303@gmail.com",os.environ["KWORLD365COM"])
s=requests.Session()
s.auth=AUTH
items=[]
page=1
while True:
    r=s.get(f"{SITE}/wp-json/wp/v2/posts",params={"per_page":100,"page":page,"status":"publish","context":"edit"},timeout=40)
    r.raise_for_status()
    batch=r.json()
    items.extend(batch)
    if len(batch)<100:break
    page+=1
results=[]
for p in items:
    id=p["id"]
    old=p["content"].get("raw") or p["content"]["rendered"]
    updated=replace(old)
    if updated==old:
        print("UNCHANGED",id,flush=True)
        continue
    response=s.post(f"{SITE}/wp-json/wp/v2/posts/{id}",json={"content":updated},timeout=45)
    response.raise_for_status()
    check=response.json()
    assert check["id"]==id and check["featured_media"]==p["featured_media"]
    assert check["tags"]==p["tags"] and check["categories"]==p["categories"]
    assert check["content"]["rendered"].count(MARKER)==1
    results.append({"id":id,"url":check["link"]})
    print("FOOTER_OK",id,flush=True)
print("TOTAL",len(items),"UPDATED",len(results),flush=True)
Path("kworld-footer-results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
