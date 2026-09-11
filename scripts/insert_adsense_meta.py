#!/usr/bin/env python3
"""insert_adsense_meta.py - AdSense 메타태그 27개 삽입"""
import os, requests, time

WP_USER = "huh0303@gmail.com"
PUB_ID  = "pub-3456727916386941"

ADSENSE_META = f'''<meta name="google-adsense-account" content="ca-{PUB_ID}">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{PUB_ID}" crossorigin="anonymous"></script>'''

SITES = [
    ("https://k-health365.com","KHEALTH365COM"),
    ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com","KOREAINVEST365COM"),
    ("https://ki-korea.com","KIKOREACOM"),
    ("https://koreainsurance365.com","KOREAINSURANCE365COM"),
    ("https://kfinance365.com","KFINANCE365COM"),
    ("https://koreataxnlaw.com","KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com","KOREACRYPTO365COM"),
    ("https://krealestate365.com","KREALESTATE365COM"),
    ("https://ktech365.com","KTECH365COM"),
    ("https://kskin365.com","KSKIN365COM"),
    ("https://oliveyoungkorea.com","OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com","KWORLD365COM"),
    ("https://k-trip365.com","KTRIP365COM"),
    ("https://k-visa365.com","KVISA365COM"),
    ("https://koreawedding365.com","KOREAWEDDING365COM"),
    ("https://kstudy365.com","KSTUDY365COM"),
    ("https://studyinkorea365.com","STUDYINKOREA365COM"),
    ("https://kieca-korea.org","KIECAKOREAORG"),
    ("https://ksa-korea.org","KSAKOREAORG"),
    ("https://sis-korea.com","SISKOREACOM"),
    ("https://jobkorea365.com","JOBKOREA365COM"),
    ("https://jobinkorea365.com","JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com","JOBKOREAGLOBALCOM"),
    ("https://korea365.org","KOREA365ORG"),
    ("https://koreanews365.com","KOREANEWS365COM"),
    ("https://theseouljournal.com","THESEOULJOURNALCOM"),
]

def insert(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    dom  = url.replace("https://","")

    snippet = {
        "title": "AdSense Meta + Script",
        "content": ADSENSE_META,
        "code_type": "html",
        "location": "site_header",
        "status": "publish",
    }

    # 기존 삭제
    try:
        r = requests.get(f"{base}/wpcode-snippets", auth=auth,
                        params={"per_page":100}, timeout=10)
        if r.status_code == 200 and isinstance(r.json(), list):
            for s in r.json():
                t = s.get("title",{})
                ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                if "adsense" in ts.lower() or "adsbygoogle" in ts.lower():
                    requests.delete(f"{base}/wpcode-snippets/{s['id']}",
                                   auth=auth, params={"force":True}, timeout=8)
    except: pass

    # 새로 생성
    try:
        cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                          json=snippet, timeout=15)
        if cr.status_code in (200,201):
            print(f"  ✅ {dom}")
            return True
        print(f"  ⚠️ {dom} ({cr.status_code})")
        return False
    except Exception as e:
        print(f"  ❌ {dom}: {e}")
        return False

print("="*55)
print("AdSense 메타태그 + 스크립트 27개 삽입")
print("="*55)
ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env,"")
    if not pw:
        print(f"  ⏭️  {url.replace('https://','')}")
        skip+=1; continue
    if insert(url, pw): ok+=1
    time.sleep(0.5)
print(f"\n✅ 성공:{ok} | ⏭️ 스킵:{skip}")
