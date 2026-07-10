#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""delete_all_dummy.py — 27개 사이트 더미글 전수삭제 + 결과 GitHub API 커밋"""
import os, requests, time, re, sys, json, base64

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GITHUB_TOKEN","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","huh0303-cmyk/-WP-QWEN-autobot")

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
    ("https://kieca-korea.org",         "KIECAKOREAORG"),
    ("https://ksa-korea.org",           "KSAKOREAORG"),
    ("https://sis-korea.com",           "SISKOREACOM"),
    ("https://jobkorea365.com",         "JOBKOREA365COM"),
    ("https://jobinkorea365.com",       "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",      "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",            "KOREA365ORG"),
    ("https://koreanews365.com",        "KOREANEWS365COM"),
    ("https://theseouljournal.com",     "THESEOULJOURNALCOM"),
]

DUMMY_PATTERNS = [
    r"^post-\d+$", r"^\d+$", r"^page-\d+$",
    r"^sample-page$", r"^hello-world$", r"^auto-draft",
]

def is_dummy_slug(slug):
    for pat in DUMMY_PATTERNS:
        if re.match(pat, slug, re.IGNORECASE):
            return True
    return slug in ("post","posts","page","pages")

def plain(html):
    return re.sub(r"<[^>]+>","",html or "").strip()

def commit_result(data):
    if not GH_TOKEN:
        return
    content = base64.b64encode(json.dumps(data,ensure_ascii=False,indent=2).encode()).decode()
    gh_headers = {"Authorization": f"token {GH_TOKEN}", "Content-Type": "application/json"}
    path = "dummy_delete_result.json"
    r = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}", headers=gh_headers, timeout=10)
    sha = r.json().get("sha","") if r.status_code==200 else ""
    payload = {"message":"result: 더미삭제 완료","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_headers, json=payload, timeout=15)
    if "content" in r2.json():
        print("✅ 결과파일 GitHub 커밋 완료")
    else:
        print(f"⚠️  결과파일 커밋 실패: {r2.json()}")

results       = []
grand_deleted = 0
grand_ok      = 0
grand_failed  = 0

print("="*60)
print("27개 사이트 더미글 전수삭제")
print("="*60)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        print(f"\n⚠️  {site_url} — Secret없음 스킵")
        sys.stdout.flush()
        continue

    base_url = f"{site_url}/wp-json/wp/v2"
    auth     = (WP_USER, pw)
    site_del = 0
    site_ok  = 0
    del_list = []

    print(f"\n🌐 {site_url}")
    sys.stdout.flush()

    for st in ["publish","draft","future","private","trash"]:
        page = 1
        while True:
            try:
                r = requests.get(f"{base_url}/posts", auth=auth,
                    params={"per_page":100,"page":page,"status":st,
                            "_fields":"id,slug,title,content"},
                    timeout=30)
                if r.status_code in (400,401,403): break
                if r.status_code != 200: break
                posts = r.json()
                if not posts: break

                for p in posts:
                    pid        = p.get("id")
                    slug       = p.get("slug","")
                    title      = p.get("title",{})
                    t_raw      = title.get("rendered","") if isinstance(title,dict) else str(title)
                    title_text = plain(t_raw)
                    body       = p.get("content",{})
                    body_text  = plain(body.get("rendered","") if isinstance(body,dict) else "")

                    dummy = False; reason = ""
                    if is_dummy_slug(slug):
                        dummy=True; reason=f"더미슬러그({slug})"
                    elif not title_text and len(body_text)<50:
                        dummy=True; reason="제목+본문없음"

                    if dummy:
                        try:
                            rd = requests.delete(f"{base_url}/posts/{pid}",
                                auth=auth, params={"force":"true"}, timeout=15)
                            if rd.status_code in (200,201,204,410):
                                print(f"  ✅ 삭제 [{pid}] {slug:30s} | {reason}")
                                site_del+=1; grand_deleted+=1
                                del_list.append({"id":pid,"slug":slug,"reason":reason})
                            else:
                                print(f"  ❌ 실패 [{pid}] {slug} HTTP={rd.status_code}")
                                grand_failed+=1
                        except Exception as e:
                            print(f"  ⚠️  [{pid}] {e}")
                            grand_failed+=1
                        time.sleep(0.3)
                        sys.stdout.flush()
                    else:
                        site_ok+=1; grand_ok+=1

                if len(posts)<100: break
                page+=1; time.sleep(0.2)
            except Exception as e:
                print(f"  ⚠️ {st} 오류: {e}")
                sys.stdout.flush()
                break

    results.append({"site":site_url,"deleted":site_del,"ok":site_ok,"list":del_list})
    print(f"  → 삭제:{site_del} | 보존:{site_ok}")
    sys.stdout.flush()
    time.sleep(0.5)

# GitHub에 결과 커밋
final = {"grand_deleted":grand_deleted,"grand_ok":grand_ok,"grand_failed":grand_failed,"sites":results}
commit_result(final)

print(f"\n{'='*60}")
print(f"✅ 완료 | 삭제:{grand_deleted} | 보존:{grand_ok} | 실패:{grand_failed}")
print(f"{'='*60}")
