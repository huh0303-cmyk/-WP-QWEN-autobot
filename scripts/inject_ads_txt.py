#!/usr/bin/env python3
"""inject_ads_txt.py v3.0 - 27개 사이트 ads.txt 강제 주입"""
import os, requests, time

PUB_ID   = "pub-3456727916386941"
ADS_LINE = "google.com, pub-3456727916386941, DIRECT, f08c47fec0942fa0"
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

def make_php_code(ads_line):
    """PHP 코드 생성 (이스케이프 없이 깔끔하게)"""
    return (
        "<?php\n"
        "add_action('init', function() {\n"
        "    if (!isset($_SERVER['REQUEST_URI'])) return;\n"
        "    $uri = strtok($_SERVER['REQUEST_URI'], '?');\n"
        "    if ($uri === '/ads.txt') {\n"
        "        header('Content-Type: text/plain; charset=utf-8');\n"
        "        header('Cache-Control: public, max-age=3600');\n"
        "        echo '" + ads_line + "';\n"
        "        exit;\n"
        "    }\n"
        "}, 1);\n"
    )

def inject_ads(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    
    # 현재 ads.txt 확인
    try:
        r = requests.get(f"{url}/ads.txt", timeout=8,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and PUB_ID in r.text:
            return "✅ 이미정상"
    except:
        pass
    
    php_code = make_php_code(ADS_LINE)
    
    snippet_data = {
        "title": "ads.txt Generator",
        "content": php_code,
        "code_type": "php",
        "location": "everywhere",
        "status": "publish",
    }
    
    # 기존 스니펫 삭제
    try:
        r2 = requests.get(f"{base}/wpcode-snippets", auth=auth,
                         params={"per_page": 100}, timeout=10)
        if r2.status_code == 200 and isinstance(r2.json(), list):
            for s in r2.json():
                t = s.get("title", {})
                ts = t.get("rendered", "") if isinstance(t, dict) else str(t)
                if "ads.txt" in ts.lower() or "adsense" in ts.lower():
                    requests.delete(
                        f"{base}/wpcode-snippets/{s['id']}",
                        auth=auth,
                        params={"force": True},
                        timeout=8
                    )
    except:
        pass
    
    # 새로 생성
    try:
        cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                          json=snippet_data, timeout=15)
        if cr.status_code in (200, 201):
            return f"✅ 삽입완료"
        return f"⚠️ {cr.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:25]}"


def run():
    ok = skip = fail = 0
    print(f"{'#':>2} {'도메인':<30} {'결과'}")
    print("=" * 55)
    
    for i, (url, env) in enumerate(SITES, 1):
        pw  = os.getenv(env, "")
        dom = url.replace("https://", "")
        
        if not pw:
            print(f"{i:>2} {dom:<30} ⏭️  비번없음")
            skip += 1
            continue
        
        result = inject_ads(url, pw)
        print(f"{i:>2} {dom:<30} {result}")
        
        if "✅" in result:
            ok += 1
        else:
            fail += 1
        
        time.sleep(0.5)
    
    print("=" * 55)
    print(f"✅ 성공:{ok} | ⏭️  스킵:{skip} | ❌ 실패:{fail}")
    
    if fail > 0:
        raise SystemExit(f"{fail}개 실패")


if __name__ == "__main__":
    run()
