#!/usr/bin/env python3
"""27개 사이트 더미글 삭제 + 2000자 미만 삭제"""
import os, requests, re, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",    "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",      "KOREAINVEST365COM"),
    ("https://ki-korea.com",            "KIKOREACOM"),
    ("https://koreainsurance365.com",   "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",         "KFINANCE365COM"),
    ("https://koreataxnlaw.com",        "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",      "KOREACRYPTO365COM"),
    ("https://krealestate365.com",      "KREALESTATE365COM"),
    ("https://ktech365.com",            "KTECH365COM"),
    ("https://kskin365.com",            "KSKIN365COM"),
    ("https://oliveyoungkorea.com",     "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",           "KWORLD365COM"),
    ("https://k-trip365.com",           "KTRIP365COM"),
    ("https://k-visa365.com",           "KVISA365COM"),
    ("https://koreawedding365.com",     "KOREAWEDDING365COM"),
    ("https://kstudy365.com",           "KSTUDY365COM"),
    ("https://studyinkorea365.com",     "STUDYINKOREA365COM"),
    ("https://jobkorea365.com",         "JOBKOREA365COM"),
    ("https://jobinkorea365.com",       "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",      "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",            "KOREA365ORG"),
    ("https://koreanews365.com",        "KOREANEWS365COM"),
    ("https://theseouljournal.com",     "THESEOULJOURNALCOM"),
]

DUMMY_SLUGS = re.compile(
    r"^(post-\d+|hello-world|sample-page|auto-draft|\d+|page-\d+|"
    r"blog-post[_-]\d+|\d{4}[-_]\d+|test[-_]|draft[-_]).*$"
)

def plain(html):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",html or "")).strip()

def char_count(html):
    return len(plain(html).replace(" ","").replace("\n",""))

grand = {"dummy":0,"short":0,"kept":0,"sites":0}

print("="*55)
print("27개 사이트 더미글+2000자미만 삭제")
print("="*55)

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw: continue
    
    domain = site_url.replace("https://","")
    auth   = ("huh0303@gmail.com", pw)
    base   = f"{site_url}/wp-json/wp/v2"
    s = {"dummy":0,"short":0,"kept":0}
    grand["sites"] += 1

    print(f"\n🌐 {domain}")
    sys.stdout.flush()

    page = 1
    while True:
        try:
            r = requests.get(f"{base}/posts", auth=auth,
                           params={"per_page":50,"page":page,"status":"publish",
                                   "_fields":"id,slug,content"}, timeout=20)
            if r.status_code != 200 or not r.json(): break
            posts = r.json()
        except: break

        for p in posts:
            pid  = p.get("id")
            slug = p.get("slug","")
            body = p.get("content",{}).get("rendered","") if isinstance(p.get("content"),dict) else ""
            chars = char_count(body)

            # 더미글
            if DUMMY_SLUGS.match(slug):
                try:
                    rd = requests.delete(f"{base}/posts/{pid}",auth=auth,
                                        params={"force":"true"},timeout=10)
                    if rd.status_code in (200,201,204,410):
                        s["dummy"]+=1; grand["dummy"]+=1
                        print(f"  🗑️ 더미 [{pid}] {slug}")
                except: pass
                time.sleep(0.15)
                continue

            # 2000자 미만
            if chars < 2000:
                try:
                    rd = requests.delete(f"{base}/posts/{pid}",auth=auth,
                                        params={"force":"true"},timeout=10)
                    if rd.status_code in (200,201,204,410):
                        s["short"]+=1; grand["short"]+=1
                        print(f"  🗑️ 짧은글 [{pid}] {chars}자")
                except: pass
                time.sleep(0.15)
                continue

            s["kept"]+=1
        
        if len(posts)<50: break
        page+=1
        time.sleep(0.3)

    print(f"  → 더미:{s['dummy']} 짧은글:{s['short']} 보존:{s['kept']}")

# 저장
result = grand
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "cleanup_27sites_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 27개 더미+짧은글 삭제","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*55}")
print(f"✅ 완료")
print(f"   더미글 삭제:    {grand['dummy']}개")
print(f"   2000자미만 삭제: {grand['short']}개")
print(f"   처리 사이트:    {grand['sites']}개")
print(f"{'='*55}")
