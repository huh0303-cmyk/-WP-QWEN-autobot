#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insert a neutral Coupang Home affiliate CTA into all published posts on eligible WP sites.
Preserves publication status/date/featured image and all existing post content.
Idempotent: one stable marker per post; verifies every write by REST read-back.
"""
import os, sys, time, json, html, re
import requests
from requests.auth import HTTPBasicAuth

WP_USER = os.getenv("WP_USER", "huh0303@gmail.com")
AFFILIATE_URL = "https://link.coupang.com/a/ihRMHfQzKf"
MARKER = "<!-- coupang-home-partners-cta-20261031 -->"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
CTA = f"""
{MARKER}
<section class="coupang-home-partners-cta" style="margin:28px 0;padding:18px;border:1px solid #e5e7eb;border-radius:10px;text-align:center;">
  <p style="margin:0 0 12px;font-weight:600;">필요한 상품을 더 찾아보고 싶으신가요?</p>
  <a href="{AFFILIATE_URL}" target="_blank" rel="sponsored nofollow noopener" style="display:inline-block;padding:11px 22px;background:#1769aa;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">쿠팡에서 상품 둘러보기</a>
  <p style="font-size:12px;color:#666;margin:12px 0 0;">{DISCLOSURE}</p>
</section>
"""
# Explicitly protected by prior user instruction; The Seoul Journal excluded from this WP batch.
SITES = [
 ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM"),
 ("https://koreainvest365.com","KOREAINVEST365COM"),
 ("https://ki-korea.com","KIKOREACOM"),
 ("https://koreainsurance365.com","KOREAINSURANCE365COM"),
 ("https://kfinance365.com","KFINANCE365COM"),
 ("https://koreataxnlaw.com","KOREATAXNLAWCOM"),
 ("https://koreacrypto365.com","KOREACRYPTO365COM"),
 ("https://ktech365.com","KTECH365COM"),
 ("https://kskin365.com","KSKIN365COM"),
 ("https://k-trip365.com","KTRIP365COM"),
 ("https://k-visa365.com","KVISA365COM"),
 ("https://koreawedding365.com","KOREAWEDDING365COM"),
 ("https://kstudy365.com","KSTUDY365COM"),
 ("https://studyinkorea365.com","STUDYINKOREA365COM"),
 ("https://kieca-korea.org","KIECAKOREAORG"),
 ("https://sis-korea.com","SISKOREACOM"),
 ("https://jobkorea365.com","JOBKOREA365COM"),
 ("https://jobinkorea365.com","JOBINKOREA365COM"),
 ("https://jobkoreaglobal.com","JOBKOREAGLOBALCOM"),
 ("https://korea365.org","KOREA365ORG"),
 ("https://koreanews365.com","KOREANEWS365COM"),
]

def request(session, method, url, **kwargs):
    for attempt in range(4):
        r = session.request(method, url, timeout=35, **kwargs)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 * (attempt + 1)); continue
        return r
    return r

def site_run(base, secret_name, dry_run):
    pw = os.getenv(secret_name, "")
    if not pw:
        return {"site":base,"status":"NO_SECRET","scanned":0,"inserted":0,"already":0,"failed":0}
    s = requests.Session()
    s.auth = HTTPBasicAuth(WP_USER,pw)
    scanned=inserted=already=failed=0
    page=1
    while True:
        r=request(s,"GET",f"{base}/wp-json/wp/v2/posts",params={
          "status":"publish","per_page":100,"page":page,"orderby":"date","order":"desc",
          "_fields":"id,link,date,date_gmt,modified,featured_media,status,content"
        })
        if r.status_code != 200:
            return {"site":base,"status":f"LIST_HTTP_{r.status_code}","scanned":scanned,"inserted":inserted,"already":already,"failed":failed,"detail":r.text[:300]}
        posts=r.json()
        if not posts: break
        for p in posts:
            scanned += 1
            raw=p.get("content",{}).get("raw") or p.get("content",{}).get("rendered") or ""
            if MARKER in raw or AFFILIATE_URL in raw:
                already += 1; continue
            if dry_run:
                continue
            # append CTA to the existing content; if raw unavailable, rendered content is used
            new_content = raw.rstrip() + "\n" + CTA
            u=request(s,"POST",f"{base}/wp-json/wp/v2/posts/{p['id']}",json={"content":new_content})
            if u.status_code not in (200,201):
                failed += 1; print(f"FAIL {base} post={p['id']} HTTP={u.status_code} {u.text[:160]}",flush=True); continue
            # Read-after-write verification
            v=request(s,"GET",f"{base}/wp-json/wp/v2/posts/{p['id']}",params={"context":"edit","_fields":"id,status,date,date_gmt,featured_media,content"})
            if v.status_code == 200:
                q=v.json(); body=q.get("content",{}).get("raw") or q.get("content",{}).get("rendered") or ""
                ok=(MARKER in body and AFFILIATE_URL in body and DISCLOSURE in body and
                    q.get("status")==p.get("status") and q.get("date")==p.get("date") and
                    q.get("featured_media")==p.get("featured_media"))
                if ok: inserted += 1
                else:
                    failed += 1; print(f"VERIFY_FAIL {base} post={p['id']}",flush=True)
            else:
                failed += 1; print(f"READBACK_FAIL {base} post={p['id']} HTTP={v.status_code}",flush=True)
            time.sleep(0.15)
        if len(posts)<100: break
        page+=1
    return {"site":base,"status":"DRY_RUN" if dry_run else "DONE","scanned":scanned,"inserted":inserted,"already":already,"failed":failed}

def main():
    dry_run=os.getenv("DRY_RUN","true").lower()=="true"
    results=[]
    for base,key in SITES:
        try:
            result=site_run(base,key,dry_run); results.append(result)
            print(json.dumps(result,ensure_ascii=False),flush=True)
        except Exception as e:
            result={"site":base,"status":"ERROR","error":str(e),"scanned":0,"inserted":0,"already":0,"failed":1}
            results.append(result); print(json.dumps(result,ensure_ascii=False),flush=True)
    with open("coupang_home_rollout_report.json","w",encoding="utf-8") as f: json.dump(results,f,ensure_ascii=False,indent=2)
    print("TOTAL "+json.dumps({k:sum(x.get(k,0) for x in results) for k in ("scanned","inserted","already","failed")},ensure_ascii=False),flush=True)
    if any(x.get("failed",0)>0 or x.get("status") not in ("DONE","DRY_RUN","NO_SECRET") for x in results): sys.exit(1)
if __name__=="__main__": main()
