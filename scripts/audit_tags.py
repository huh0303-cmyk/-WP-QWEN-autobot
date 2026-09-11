#!/usr/bin/env python3
import os, requests, json, base64

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

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

results = {}
for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        results[site_url] = {"tags":0,"cats":0,"error":"no_pw"}
        continue
    auth = (WP_USER, pw)
    try:
        rt = requests.get(f"{site_url}/wp-json/wp/v2/tags?per_page=1",
                         auth=auth, timeout=10)
        rc = requests.get(f"{site_url}/wp-json/wp/v2/categories?per_page=1",
                         auth=auth, timeout=10)
        tags = int(rt.headers.get("X-WP-Total",0)) if rt.status_code==200 else 0
        cats = int(rc.headers.get("X-WP-Total",0)) if rc.status_code==200 else 0
        results[site_url] = {"tags":tags,"cats":cats}
        print(f"  {site_url}: 태그{tags} 카테{cats}")
    except Exception as e:
        results[site_url] = {"tags":0,"cats":0,"error":str(e)[:50]}

if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "site_tags_audit.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 태그 수 전수 조사","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, json=payload, timeout=15)
    print(f"저장: {'OK' if 'content' in r2.json() else 'FAIL'}")
print("완료")
