#!/usr/bin/env python3
import os, requests, time, re, html

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com",       "KHEALTH365COM",        "ko"),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM",  "en"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM",    "en"),
    ("https://ki-korea.com",           "KIKOREACOM",           "en"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM", "en"),
    ("https://kfinance365.com",        "KFINANCE365COM",       "en"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM",      "en"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM",    "en"),
    ("https://krealestate365.com",     "KREALESTATE365COM",    "en"),
    ("https://ktech365.com",           "KTECH365COM",          "en"),
    ("https://kskin365.com",           "KSKIN365COM",          "en"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM",   "en"),
    ("https://kworld365.com",          "KWORLD365COM",         "en"),
    ("https://k-trip365.com",          "KTRIP365COM",          "en"),
    ("https://k-visa365.com",          "KVISA365COM",          "en"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM",   "en"),
    ("https://kstudy365.com",          "KSTUDY365COM",         "en"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM",   "en"),
    ("https://kieca-korea.org",        "KIECAKOREAORG",        "en"),
    ("https://ksa-korea.org",          "KSAKOREAORG",          "en"),
    ("https://sis-korea.com",          "SISKOREACOM",          "en"),
    ("https://jobkorea365.com",        "JOBKOREA365COM",       "en"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM",     "en"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM",    "en"),
    ("https://korea365.org",           "KOREA365ORG",          "en"),
    ("https://koreanews365.com",       "KOREANEWS365COM",      "ko"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM",   "en"),
]

YEAR_RE = re.compile(r'\b202[0-5]\b|202[0-5]년')
CLICHE  = re.compile(
    r'complete guide to|ultimate guide|everything you need|a to z|'
    r'top \d+ (?:reasons|tips|ways)|총정리|완벽\s*가이드|모든\s*것|알아보자',
    re.I)

def audit(url, pw, lang):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    all_posts = []
    page = 1
    while True:
        r = requests.get(f"{base}/posts", auth=auth,
                        params={"per_page":100,"page":page,"status":"publish",
                                "_fields":"id,title,content,meta"},
                        timeout=20)
        if r.status_code != 200 or not isinstance(r.json(),list) or not r.json():
            break
        all_posts.extend(r.json())
        if len(r.json()) < 100: break
        page += 1

    total = len(all_posts)
    delete_set = set()

    title_seen = {}
    for p in all_posts:
        pid = p["id"]
        t   = p.get("title",{})
        title = html.unescape(re.sub('<[^>]+>','',
                t.get("rendered","") if isinstance(t,dict) else str(t))).strip()
        c   = p.get("content",{})
        body = re.sub('<[^>]+>','',
               c.get("rendered","") if isinstance(c,dict) else str(c))
        body_len = len(body.replace(' ','').replace('\n',''))

        # SEO 점수
        meta = p.get("meta",{})
        seo  = meta.get("rank_math_seo_score","") if isinstance(meta,dict) else ""
        try: seo_int = int(float(str(seo))) if seo else 0
        except: seo_int = 0

        reasons = []

        # 1. 연도 포함
        if YEAR_RE.search(title):
            reasons.append("연도")

        # 2. 진부한 패턴
        if CLICHE.search(title.lower()):
            reasons.append("진부패턴")

        # 3. 중복 제목
        key = re.sub(r'\s+','',title[:20].lower())
        if key in title_seen:
            reasons.append("중복")
        else:
            title_seen[key] = pid

        # 4. 본문 너무 짧음
        if body_len < 800:
            reasons.append(f"짧음({body_len}자)")

        # 5. SEO 90점 미만
        if 0 < seo_int < 90:
            reasons.append(f"SEO({seo_int})")

        if reasons:
            delete_set.add(pid)

    return total, len(delete_set), total - len(delete_set)

print(f"{'#':>2} {'도메인':<28} {'전체':>6} {'삭제대상':>8} {'잔류예상':>8}")
print("="*58)

results = []
for i,(url,env,lang) in enumerate(SITES,1):
    pw = os.getenv(env,"")
    dom = url.replace("https://","")
    if not pw:
        print(f"{i:>2} {dom:<28} {'비번없음':>6}")
        results.append((dom,0,0,0))
        continue
    try:
        total, delete, remain = audit(url, pw, lang)
        print(f"{i:>2} {dom:<28} {total:>6} {delete:>8} {remain:>8}")
        results.append((dom, total, delete, remain))
    except Exception as e:
        print(f"{i:>2} {dom:<28} {'오류':>6}")
        results.append((dom,0,0,0))
    time.sleep(0.5)

print("="*58)
total_all   = sum(r[1] for r in results)
delete_all  = sum(r[2] for r in results)
remain_all  = sum(r[3] for r in results)
print(f"{'합계':<30} {total_all:>6} {delete_all:>8} {remain_all:>8}")
