import json, re, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "reports" / "koreawedding365-8-category-captures-2026-11-01.ndjson"
MAP = ROOT / "data" / "affiliate" / "fleet-placements.json"
BASE = "https://koreawedding365.com"
DISPLAY = {
 "kw01":"White Calla Artificial Wedding Bouquet",
 "kw02":"Two-Layer Bridal Veil for Self-Wedding and Bridal Shower",
 "kw09":"Traditional Korean Hanbok Hairpin",
 "kw10":"Mother-of-Pearl Korean Jewelry Box",
 "kw33":"Korean Red Ginseng Mild Sachets",
 "kw34":"BYO Core Probiotic Supplement",
 "kw13":"Dyson Airwrap Co-anda2x Multi-Styler",
 "kw25":"Medicube Age-R Booster Pro X2 Beauty Device",
}
CATEGORY = {
 "kw01":"topic","kw02":"topic",
 "kw09":"korean_life","kw10":"korean_life",
 "kw33":"health","kw34":"health",
 "kw13":"kbeauty","kw25":"kbeauty",
}

products=[]
for line in CAPTURE.read_text(encoding="utf-8-sig").splitlines():
 if not line.strip(): continue
 p=json.loads(line)
 cid=p["candidate_id"]
 tag=p.get("official_blog_html_tag","")
 banner=re.search(r'<img[^>]+src="([^"]+)"',tag,re.I)
 if p.get("status")!="CAPTURED" or not banner:
  raise SystemExit("Unverified capture: "+cid)
 p["official_image_url"]=banner.group(1)
 p["category"]=CATEGORY[cid]
 p["verified_account_owned"]=True
 p["capture_source"]="coupang_partners_portal"
 p["product_title"]=DISPLAY[cid]
 if p["affiliate_url"] not in tag or p["official_image_url"] not in tag:
  raise SystemExit("Affiliate tag mismatch: "+cid)
 products.append(p)
if len(products)!=8 or len({p["affiliate_url"] for p in products})!=8:
 raise SystemExit(f"Expected 8 unique products, got {len(products)}")
counts={k:sum(1 for p in products if p["category"]==k) for k in ("topic","korean_life","health","kbeauty")}
if counts!={"topic":2,"korean_life":2,"health":2,"kbeauty":2}:
 raise SystemExit("Category balance mismatch: "+str(counts))

s=requests.Session()
s.headers["User-Agent"]="LondonProject-KoreaWedding365-Affiliate-Map/1.0"
posts=[]
for page in range(1,10):
 r=s.get(BASE+"/wp-json/wp/v2/posts",params={"status":"publish","per_page":100,"page":page,"_fields":"id,status,modified,link,title"},timeout=45)
 if r.status_code==400 and page>1: break
 r.raise_for_status()
 batch=r.json()
 if not batch: break
 posts.extend(batch)
 if len(batch)<100: break
if not posts: raise SystemExit("No published posts returned")
if any(p.get("status")!="publish" for p in posts): raise SystemExit("Non-published post returned")
seen=set(); posts=[p for p in posts if not (p["id"] in seen or seen.add(p["id"]))]
entries=[]
for post in posts:
 entries.append({
  "post_id":post["id"],
  "link":post["link"],
  "title":post.get("title",{}).get("rendered",""),
  "modified_snapshot":post.get("modified"),
  "products":products
 })
data=json.loads(MAP.read_text(encoding="utf-8-sig")) if MAP.exists() else {"sites":{}}
data.setdefault("sites",{})["koreawedding365.com"]=entries
MAP.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({
 "site":BASE,
 "published_posts":len(posts),
 "unique_products":len(products),
 "category_counts":counts,
 "affiliate_links":len({p["affiliate_url"] for p in products}),
 "map_path":str(MAP)
},ensure_ascii=False,indent=2))
