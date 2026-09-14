#!/usr/bin/env python3
"""Read-only inventory of every Koreanews post status."""
import json,os,requests
from pathlib import Path
USER=os.getenv("WP_USER","").strip() or "huh0303@gmail.com"
PW=os.getenv("KOREANEWS365COM","").strip()
BASE="https://koreanews365.com/wp-json/wp/v2"
rows=[]
for status in ("publish","private","draft","pending","future"):
    page=1
    while True:
        r=requests.get(f"{BASE}/posts",auth=(USER,PW),params={"context":"edit","status":status,"per_page":100,"page":page,
          "_fields":"id,date,modified,slug,link,title,excerpt,content,categories,status"},timeout=40)
        if r.status_code==400 and "rest_post_invalid_page_number" in r.text:break
        r.raise_for_status();batch=r.json()
        rows.extend(batch)
        if page>=int(r.headers.get("X-WP-TotalPages","1")):break
        page+=1
Path("koreanews_all_posts_inventory.json").write_text(json.dumps({"count":len(rows),"posts":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"count":len(rows),"by_status":{s:sum(1 for p in rows if p["status"]==s) for s in ("publish","private","draft","pending","future")},
 "posts":[{"id":p["id"],"status":p["status"],"date":p["date"],"title":p["title"]["raw"],"categories":p["categories"]} for p in rows]},ensure_ascii=False,indent=2))
