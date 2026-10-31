#!/usr/bin/env python3
"""Build verified Coupang product cards for the K-Health365 pilot post."""
from __future__ import annotations
import base64, html, json, os, random, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://k-health365.com"
ALLOWED_POST_ID = 6148
START = "<!-- KHEALTH365_AFFILIATE_CARDS_START -->"
END = "<!-- KHEALTH365_AFFILIATE_CARDS_END -->"
CATALOG = Path("config/affiliate/k-health365-products.json")
OUT = Path("output")
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

def fail(message):
    raise SystemExit("ERROR: " + str(message))

def request(url, method="GET", payload=None, auth=None):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept":"application/json", "Content-Type":"application/json"}
    if auth: headers["Authorization"] = "Basic " + auth
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as e:
        fail("WordPress HTTP %s: %s" % (e.code, e.read(1000).decode("utf-8","replace")))
    except Exception as e:
        fail("Request failed: " + str(e))

def resolve_product_image(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            page_url = r.geturl()
            page = r.read(4000000).decode("utf-8","replace")
    except Exception as e:
        fail("Coupang link could not be opened (%s): %s" % (url,e))
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        r'(https://[^"\'\\s<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^"\'\\s<>]*)?)'
    ]
    candidates=[]
    for pat in patterns: candidates.extend(re.findall(pat,page,re.I))
    seen=set()
    for candidate in candidates:
        image_url=urllib.parse.urljoin(page_url,html.unescape(candidate).replace("\\/","/"))
        parsed=urllib.parse.urlparse(image_url)
        if parsed.scheme!="https" or not parsed.path.lower().endswith((".jpg",".jpeg",".png",".webp")) or image_url in seen: continue
        seen.add(image_url)
        try:
            check=urllib.request.Request(image_url,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(check,timeout=15) as img:
                if img.status==200 and img.headers.get("Content-Type","").lower().startswith("image/"):
                    return image_url
        except Exception: pass
    fail("No live, verified product image found for: " + url)

def main():
    post_id=int(os.getenv("POST_ID","6148"))
    if post_id!=ALLOWED_POST_ID: fail("Pilot is restricted to post 6148.")
    lo,hi=int(os.getenv("MIN_ITEMS","5")),int(os.getenv("MAX_ITEMS","10"))
    if not (5<=lo<=hi<=10): fail("Require 5 <= MIN_ITEMS <= MAX_ITEMS <= 10.")
    mode=os.getenv("MODE","preview")
    if mode not in ("preview","apply"): fail("MODE must be preview or apply.")
    products=json.loads(CATALOG.read_text(encoding="utf-8"))
    eligible=[]
    for p in products:
        if not p.get("enabled") or not p.get("affiliate_confirmed"): continue
        if not all(p.get(k) for k in ("title","url","relevance")): continue
        if urllib.parse.urlparse(p["url"]).scheme!="https": continue
        p=dict(p)
        p["image_url"]=resolve_product_image(p["url"])
        eligible.append(p)
    if len(eligible)<lo:
        fail("Only %d products have verified images and links; at least %d required."%(len(eligible),lo))
    user=os.getenv("WP_USER",""); password=os.getenv("WP_APP_PASSWORD","")
    if not user or not password: fail("Missing KHEALTH365_WP_USER / KHEALTH365_WP_APP_PASSWORD secrets.")
    auth=base64.b64encode((user+":"+password).encode()).decode()
    site=os.getenv("WP_SITE_URL",SITE).rstrip("/")
    post=request(site+"/wp-json/wp/v2/posts/%d?context=edit"%post_id,auth=auth)
    title=html.unescape(re.sub("<[^>]+>"," ",post.get("title",{}).get("rendered","")))
    content=post.get("content",{}).get("raw")
    if content is None: fail("WordPress did not return editable raw post content.")
    relevant=[p for p in eligible if any(k.lower() in (title+" "+p["relevance"]).lower() for k in p.get("keywords",[]))]
    pool=relevant if len(relevant)>=lo else eligible
    count=min(random.randint(lo,hi),len(pool))
    chosen=random.sample(pool,count)
    parts=[START,'<section class="khealth-affiliate-products" aria-label="관련 상품 추천">','<h2>함께 확인할 만한 상품</h2>',f'<p class="khealth-affiliate-disclosure">{html.escape(DISCLOSURE)}</p>','<div class="khealth-affiliate-grid">']
    for p in chosen:
        parts.append('<article class="khealth-affiliate-card"><a href="%s" target="_blank" rel="sponsored nofollow noopener"><img src="%s" alt="%s" loading="lazy" /><h3>%s</h3><span class="khealth-affiliate-button">쿠팡에서 상품 확인하기</span></a></article>'%(html.escape(p["url"],quote=True),html.escape(p["image_url"],quote=True),html.escape(p["title"],quote=True),html.escape(p["title"])))
    parts.extend(['</div></section>',END])
    block="\n".join(parts)
    if START in content and END in content:
        before,rest=content.split(START,1)
        content=before+block+rest.split(END,1)[1]
    else:
        # Remove only the earlier manually-added product section, preserving the disclosure and article.
        content=re.sub(r'\s*<section class="khealth-affiliate-products" aria-label="관련 상품 추천">.*?</section>\s*$','',content,count=1,flags=re.S)
        content=content.rstrip()+"\n\n"+block
    OUT.mkdir(exist_ok=True)
    report={"site":site,"post_id":post_id,"post_title":title,"mode":mode,"selected_count":len(chosen),"products":[{"title":p["title"],"url":p["url"],"image_url":p["image_url"]} for p in chosen]}
    (OUT/("khealth365-affiliate-%d.json"%post_id)).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/("khealth365-affiliate-%d.html"%post_id)).write_text(block,encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if mode=="apply":
        result=request(site+"/wp-json/wp/v2/posts/%d"%post_id,"POST",{"content":content},auth)
        if result.get("id")!=post_id: fail("WordPress did not confirm target post ID.")
        verify=request(site+"/wp-json/wp/v2/posts/%d?context=edit"%post_id,auth=auth)
        raw=verify.get("content",{}).get("raw","")
        if START not in raw or END not in raw or raw.count('class="khealth-affiliate-card"')!=len(chosen):
            fail("Post update verification failed.")
        print("VERIFIED: post %d now contains %d image product cards."%(post_id,len(chosen)))
    else: print("PREVIEW ONLY: no WordPress changes.")

if __name__=="__main__": main()
