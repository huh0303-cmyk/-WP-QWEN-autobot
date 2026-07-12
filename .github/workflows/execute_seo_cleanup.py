#!/usr/bin/env python3
"""감사 결과 기반 실제 삭제/휴지통 실행"""
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

# 감사 결과 로드
import requests as req
TOKEN   = os.getenv("GH_PAT","")
REPO    = os.getenv("GITHUB_REPOSITORY","")
gh_h    = {"Authorization":f"token {TOKEN}"}
rf = req.get(f"https://api.github.com/repos/{REPO}/contents/khealth_seo_audit.json",
             headers=gh_h, timeout=10)
audit = json.loads(base64.b64decode(rf.json()["content"]).decode())

stats = {"deleted":0,"trashed":0,"errors":0}

print("="*55)
print("k-health365.com SEO 정리 실행")
print("="*55)
sys.stdout.flush()

# ── 1. 2500자 미만 영구 삭제 ──────────────────────────────
print(f"\n[1] 2500자 미만 {len(audit['delete_short'])}개 영구 삭제")
# 비정상 초대형 글 추가 (2949, 2945)
extra_delete = [2949, 2945]
delete_ids = [p["id"] for p in audit["delete_short"]] + extra_delete

for pid in delete_ids:
    try:
        r = requests.delete(f"{base}/posts/{pid}", auth=auth,
                           params={"force":"true"}, timeout=10)
        if r.status_code in (200,201,204,410):
            stats["deleted"] += 1
            print(f"  🗑️ 삭제 [{pid}]")
        else:
            stats["errors"] += 1
    except: stats["errors"] += 1
    time.sleep(0.2)

# ── 2. SEO 80점 미만 휴지통 ──────────────────────────────
print(f"\n[2] SEO 80점 미만 {len(audit['trash_seo'])}개 휴지통")
# 건강 무관 글 제외 목록 (호텔, 법인, 절세 등)
trash_ids = [p["id"] for p in audit["trash_seo"]]

for pid in trash_ids:
    try:
        r = requests.delete(f"{base}/posts/{pid}", auth=auth, timeout=10)
        if r.status_code in (200,201):
            stats["trashed"] += 1
            print(f"  🗂️ 휴지통 [{pid}]")
        else:
            stats["errors"] += 1
    except: stats["errors"] += 1
    time.sleep(0.15)

# ── 3. Blogger 이전 글 중 저품질만 휴지통 ────────────────
print(f"\n[3] Blogger 이전 글 저품질 처리")
blogger_trash = [p for p in audit["blogger_posts"]
                 if p["score"] < 70 or p["chars"] < 1500]
print(f"  저품질 {len(blogger_trash)}개 → 휴지통")
for p in blogger_trash:
    try:
        r = requests.delete(f"{base}/posts/{p['id']}", auth=auth, timeout=10)
        if r.status_code in (200,201):
            stats["trashed"] += 1
            print(f"  🗂️ [{p['id']}] {p['score']}점/{p['chars']}자 | {p['title'][:40]}")
        else:
            stats["errors"] += 1
    except: stats["errors"] += 1
    time.sleep(0.15)

# 결과 저장
result = stats
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False).encode()).decode()
    path = "khealth_cleanup_final.json"
    rg = req.get(f"https://api.github.com/repos/{REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: SEO 정리 완료","content":content}
    if sha: payload["sha"] = sha
    req.put(f"https://api.github.com/repos/{REPO}/contents/{path}",
            headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*55}")
print(f"✅ 완료")
print(f"   영구 삭제: {stats['deleted']}개")
print(f"   휴지통:    {stats['trashed']}개")
print(f"   오류:      {stats['errors']}개")
print(f"{'='*55}")
