#!/usr/bin/env python3
"""inject_ads_txt.py - 27개 사이트 ads.txt 강제 주입 v2.0"""
import os, requests, time

PUB_ID   = "pub-3456727916386941"
ADS_LINE = f"google.com, {PUB_ID}, DIRECT, f08c47fec0942fa0"
WP_USER  = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com",       "KHEALTH365COM"),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://ktech365.com",           "KTECH365COM"),
    ("https://kskin365.com",           "KSKIN365COM"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",          "KWORLD365COM"),
    ("https://k-trip365.com",          "KTRIP365COM"),
    ("https://k-visa365.com",          "KVISA365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://kstudy365.com",          "KSTUDY365COM"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",        "KIECAKOREAORG"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
    ("https://sis-korea.com",          "SISKOREACOM"),
    ("https://jobkorea365.com",        "JOBKOREA365COM"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",           "KOREA365ORG"),
    ("https://koreanews365.com",       "KOREANEWS365COM"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM"),
]

def make_php(ads_line):
    lines = [
        "<?php",
        "add_action(\'init\', function() {",
        "    if (!isset($_SERVER[\'REQUEST_URI\'])) return;",
        "    $uri = strtok($_SERVER[\'REQUEST_URI\'], \'?\');",
        "    if ($uri === \'/ads.txt\') {",
        "        header(\'Content-Type: text/plain; charset=utf-8\');",
        "        header(\'Cache-Control: public, max-age=3600\');",
        f"        echo \'{ads_line}\';",
        "        exit;",
        "    }",
        "}, 1);",
    ]
    return "\n".join(lines)

def inject(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    
    # 현재 상태 확인
    try:
        r = requests.get(f"{url}/ads.txt", timeout=8,
                        headers={"User-Agent":"Googlebot/2.1"})
        if r.status_code == 200 and PUB_ID in r.text:
            return "✅ 이미정상"
    except: pass
    
    php = make_php(ADS_LINE)
    snippet = {
        "title": "ads.txt AdSense",
        "content": php,
        "code_type": "php",
        "location": "everywhere",
        "status": "publish",
    }
    
    # 기존 삭제
    try:
        r2 = requests.get(f"{base}/wpcode-snippets", auth=auth,
                         params={"per_page":100}, timeout=10)
        if r2.status_code == 200 and isinstance(r2.json(), list):
            for s in r2.json():
                t = s.get("title",{})
                ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                if "ads.txt" in ts.lower() or "adsense" in ts.lower():
                    requests.delete(f"{base}/wpcode-snippets/{s[\'id\']}",
                                   auth=auth, params={"force":True}, timeout=8)
    except: pass
    
    # 새로 생성
    try:
        cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                          json=snippet, timeout=15)
        if cr.status_code in (200,201):
            # 삽입 후 즉시 확인
            time.sleep(2)
            rv = requests.get(f"{url}/ads.txt", timeout=8,
                             headers={"User-Agent":"Googlebot/2.1"})
            if rv.status_code == 200 and PUB_ID in rv.text:
                return "✅ 삽입+확인"
            return f"✅ 삽입완료({cr.status_code})"
        return f"⚠️{cr.status_code}"
    except Exception as e:
        return f"❌{str(e)[:20]}"

def run():
    ok = skip = fail = 0
    print(f"{'#':>2} {\'도메인\':<28} {\'결과\'}")
    print("─"*55)
    for i,(url,env) in enumerate(SITES,1):
        pw = os.getenv(env,"")
        dom = url.replace("https://","")
        if not pw:
            print(f"{i:>2} {dom:<28} ⏭️ 비번없음")
            skip+=1; continue
        result = inject(url, pw)
        print(f"{i:>2} {dom:<28} {result}")
        if "✅" in result: ok+=1
        else: fail+=1
        time.sleep(0.8)
    print("─"*55)
    print(f"✅{ok} | ⏭️{skip} | ❌{fail}")

if __name__=="__main__":
    run()
