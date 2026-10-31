#!/usr/bin/env python3
"""Append eight verified, account-generated Coupang Partners products to every published post."""
import os,json,re,html,hashlib,argparse,time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
WP_USER="huh0303@gmail.com"
SITES={
 "oliveyoungkorea":{"url":"https://oliveyoungkorea.com","secret":"OLIVEYOUNGKOREACOM"},
 "kskin365":{"url":"https://kskin365.com","secret":"KSKIN365COM"},
}
MAP_PATH="reports/oliveyoung-kskin365-affiliate-placement-map-2026-11-01.json"
START="<!-- LONDON_COUPANG_PARTNERS_START -->"
END="<!-- LONDON_COUPANG_PARTNERS_END -->"
def session(secret):
 s=requests.Session();s.auth=(WP_USER,secret);s.headers["User-Agent"]="LondonProject-CoupangPartners/1.0"
 retry=Retry(total=3,connect=3,read=3,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=["GET","POST"])
 s.mount("https://",HTTPAdapter(max_retries=retry))
 return s
def fetch(s,base,pid):
 r=s.get(f"{base}/wp-json/wp/v2/posts/{pid}",params={"context":"edit"},timeout=60);r.raise_for_status();return r.json()
def build_section(post):
 cards=[]
 for p in post["products"]:
  tag=p["official_blog_html_tag"]
  if not tag or p["affiliate_url"] not in tag or p["official_image_url"] not in tag:
   raise ValueError(f"Product tag mismatch {p['candidate_id']}")
  title=html.escape(p["display_title_en"])
  desc=html.escape(p["description_en"])
  link=html.escape(p["affiliate_url"],quote=True)
  cards.append(
   '<div class="london-coupang-product" style="box-sizing:border-box;border:1px solid #e5e7eb;border-radius:10px;padding:14px;text-align:center;min-width:0;">'
   '<div style="display:flex;justify-content:center;align-items:center;min-height:240px;">'+tag+'</div>'
   f'<p style="margin:12px 0 6px;font-weight:700;line-height:1.4;"><a href="{link}" target="_blank" rel="sponsored nofollow noopener" referrerpolicy="unsafe-url">{title}</a></p>'
   f'<p style="margin:0 0 10px;font-size:14px;line-height:1.5;">{desc}</p>'
   f'<p style="margin:0;"><a href="{link}" target="_blank" rel="sponsored nofollow noopener" referrerpolicy="unsafe-url">View current price on Coupang</a></p>'
   '</div>'
  )
 return (
  START+'\n'
  '<!-- wp:html -->\n'
  '<section class="london-coupang-partners" aria-label="Recommended K-beauty products" style="margin:36px 0 20px;padding:24px 16px;border-top:2px solid #e5e7eb;">'
  '<h2 style="margin:0 0 8px;">Recommended K-Beauty Products</h2>'
  '<p style="margin:0 0 18px;">Explore these Korean skincare and beauty picks selected to complement this article.</p>'
  '<div class="london-coupang-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;">'
  +'\n'.join(cards)+
  '</div>'
  '<p style="font-size:12px;line-height:1.5;margin:18px 0 4px;">Disclosure: This article contains Coupang Partners affiliate links. We may earn a commission from qualifying purchases at no additional cost to you.</p>'
  '<p style="font-size:11px;line-height:1.5;margin:0;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'
  '</section>\n<!-- /wp:html -->\n'
  +END
 )
def replace_section(content,section):
 if START in content and END in content:
  a=content.index(START);b=content.index(END,a)+len(END)
  return content[:a]+section+content[b:]
 return content.rstrip()+"\n\n"+section+"\n"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");ap.add_argument("--out",default="reports/oliveyoung-kskin365-affiliate-insert-2026-11-01.json");a=ap.parse_args()
 m=json.loads(Path(MAP_PATH).read_text(encoding="utf-8"))
 report={"task":"oliveyoung-kskin365-sitewide-coupang-affiliate","mode":"apply" if a.apply else "dry_run","products_per_post":8,"sites":{}}
 for site,cfg in SITES.items():
  secret=os.getenv(cfg["secret"])
  if a.apply and not secret:raise SystemExit("Missing credential env var "+cfg["secret"])
  s=session(secret) if secret else requests.Session()
  results=[]
  for item in m["sites"][site]:
   pid=item["post_id"];expected=item.get("modified_snapshot")
   try:
    p=fetch(s,cfg["url"],pid)
    if p.get("status")!="publish":raise RuntimeError("post is not published")
    if expected and p.get("modified")!=expected:
     results.append({"post_id":pid,"link":item["link"],"status":"SKIPPED_MODIFIED_AFTER_SNAPSHOT","expected_modified":expected,"actual_modified":p.get("modified")})
     continue
    raw=p.get("content",{}).get("raw")
    if raw is None:raise RuntimeError("authenticated raw post content unavailable; refusing to overwrite rendered content")
    section=build_section(item)
    new=replace_section(raw,section)
    links=[x["affiliate_url"] for x in item["products"]]
    unique=len(set(links))
    if unique!=8:raise RuntimeError(f"expected 8 unique affiliate links, found {unique}")
    existing=START in raw and END in raw
    rec={"post_id":pid,"link":item["link"],"title":item["title"],"status":"PLANNED_UPDATE" if new!=raw else "ALREADY_CURRENT","unique_products":unique,"affiliate_link_occurrences":sum(new.count(u) for u in set(links)),"section_replaced":existing}
    if a.apply and new!=raw:
     pr=s.post(f"{cfg['url']}/wp-json/wp/v2/posts/{pid}",json={"content":new},timeout=90);pr.raise_for_status()
     q=fetch(s,cfg["url"],pid);check=q.get("content",{}).get("raw") or ""
     if START not in check or END not in check:raise RuntimeError("marker missing after REST read-back")
     missing=[u for u in set(links) if u not in check]
     if missing:raise RuntimeError("affiliate links missing after REST read-back: "+str(missing))
     if sum(check.count(u) for u in set(links))<16:raise RuntimeError("expected image and title CTA for each of 8 products")
     pub=requests.get(f"{cfg['url']}/wp-json/wp/v2/posts/{pid}",timeout=45);pub.raise_for_status()
     rendered=pub.json().get("content",{}).get("rendered","")
     public_missing=[u for u in set(links) if u not in rendered]
     if public_missing:raise RuntimeError("public rendered page missing links: "+str(public_missing))
     rec["status"]="UPDATED_VERIFIED";rec["updated_fields"]=["content"];rec["public_unique_links"]=sum(1 for u in set(links) if u in rendered)
    elif a.apply:rec["status"]="ALREADY_CURRENT"
    results.append(rec)
   except Exception as e:
    results.append({"post_id":pid,"link":item.get("link"),"status":"ERROR","error":str(e)[:500]})
    if a.apply:time.sleep(0.2)
  report["sites"][site]={"posts_in_map":len(m["sites"][site]),"updated":sum(x["status"]=="UPDATED_VERIFIED" for x in results),"already_current":sum(x["status"]=="ALREADY_CURRENT" for x in results),"skipped":sum(x["status"].startswith("SKIPPED") for x in results),"errors":sum(x["status"]=="ERROR" for x in results),"results":results}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"mode":report["mode"],"sites":{k:{x:v[x] for x in ["posts_in_map","updated","already_current","skipped","errors"]} for k,v in report["sites"].items()}},ensure_ascii=False))
if __name__=="__main__":main()
