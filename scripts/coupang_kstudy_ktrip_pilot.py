#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insert and verify the user's confirmed generic Coupang Partners link on KStudy365 and K-trip365.
Pilot: latest 5 published posts per site. Idempotent; never changes post status/date/featured image.
"""
import os, json, time, sys
import requests
from requests.auth import HTTPBasicAuth

WP_USER = os.getenv("WP_USER", "huh0303@gmail.com")
AFFILIATE_URL = "https://link.coupang.com/a/ihRMHfQzKf"
MARKER = "<!-- coupang-partners-generic-cta-20261103 -->"
DISCLOSURE_MARKER = "<!-- coupang-partners-disclosure-20261103 -->"
DISCLOSURE = "이 게시물은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
CTA = f'''{MARKER}
<section class="coupang-partners-cta" style="margin:28px 0;padding:18px;border:1px solid #e5e7eb;border-radius:10px;text-align:center;">
  <p style="margin:0 0 12px;font-weight:600;">한국에서 필요한 상품을 더 찾아보세요.</p>
  <a href="{AFFILIATE_URL}" target="_blank" rel="sponsored nofollow noopener" style="display:inline-block;padding:11px 22px;background:#1769aa;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">쿠팡에서 상품 둘러보기</a>
</section>'''
DISCLOSURE_HTML = f'{DISCLOSURE_MARKER}<p class="affiliate-disclosure" style="font-size:13px;color:#555;margin:0 0 16px;">{DISCLOSURE}</p>'
SITES = [
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
]
LIMIT = int(os.getenv("POST_LIMIT_PER_SITE", "5"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

def main():
    results=[]
    for base, secret in SITES:
        pw=os.getenv(secret, "")
        if not pw:
            results.append({"site":base,"status":"NO_SECRET","scanned":0,"inserted":0,"already":0,"failed":0})
            continue
        s=requests.Session()
        s.auth=HTTPBasicAuth(WP_USER,pw)
        params={"status":"publish","per_page":LIMIT,"page":1,"orderby":"date","order":"desc",
                "context":"edit","_fields":"id,link,status,date,featured_media,content"}
        r=s.get(base+"/wp-json/wp/v2/posts",params=params,timeout=30)
        if r.status_code != 200:
            results.append({"site":base,"status":"LIST_HTTP_"+str(r.status_code),"detail":r.text[:250],"scanned":0,"inserted":0,"already":0,"failed":0})
            continue
        posts=r.json()
        counts={"site":base,"status":"DRY_RUN" if DRY_RUN else "DONE","scanned":0,"inserted":0,"already":0,"failed":0,"post_urls":[]}
        for p in posts:
            counts["scanned"]+=1
            raw=p.get("content",{}).get("raw")
            if not isinstance(raw,str):
                counts["failed"]+=1
                continue
            if MARKER in raw or AFFILIATE_URL in raw:
                counts["already"]+=1
                continue
            disclosure = "" if DISCLOSURE_MARKER in raw or DISCLOSURE in raw else DISCLOSURE_HTML+"\n"
            updated = disclosure + raw.rstrip() + "\n" + CTA
            if DRY_RUN:
                continue
            u=s.post(base+f"/wp-json/wp/v2/posts/{p['id']}",json={"content":updated},timeout=30)
            if u.status_code not in (200,201):
                counts["failed"]+=1
                continue
            v=s.get(base+f"/wp-json/wp/v2/posts/{p['id']}",params={"context":"edit","_fields":"id,link,status,date,featured_media,content"},timeout=30)
            if v.status_code != 200:
                counts["failed"]+=1
                continue
            q=v.json(); body=q.get("content",{}).get("raw","")
            ok=(MARKER in body and AFFILIATE_URL in body and DISCLOSURE in body and
                q.get("status")==p.get("status") and q.get("date")==p.get("date") and
                q.get("featured_media")==p.get("featured_media"))
            if ok:
                counts["inserted"]+=1
                counts["post_urls"].append(q.get("link"))
            else:
                counts["failed"]+=1
            time.sleep(0.2)
        results.append(counts)
        print(json.dumps(counts,ensure_ascii=False),flush=True)
    with open("coupang_kstudy_ktrip_pilot_report.json","w",encoding="utf-8") as f:
        json.dump(results,f,ensure_ascii=False,indent=2)
    totals={k:sum(x.get(k,0) for x in results) for k in ("scanned","inserted","already","failed")}
    print("TOTAL "+json.dumps(totals,ensure_ascii=False),flush=True)
    if any(x["status"] not in ("DONE","DRY_RUN","NO_SECRET") for x in results) or totals["failed"]:
        sys.exit(1)

if __name__=="__main__":
    main()
