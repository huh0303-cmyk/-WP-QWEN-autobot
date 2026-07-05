import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE = "https://k-health365.com"
pw = os.getenv("KHEALTH365COM", "")

if not pw:
    print("NO PASSWORD")
    exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=== k-health365 카테고리 5개 설정 ===")

CATS = [
    ("건강의학정보",    "health-medical-info",    "건강 의학 정보, 증상, 치료법"),
    ("건강기능식품정보", "health-supplements",     "건강기능식품, 영양제, 비타민 정보"),
    ("질환별관리법",    "disease-management",     "질환별 관리법, 예방, 치료"),
    ("건강생활정보",    "healthy-lifestyle",      "건강한 생활습관, 운동, 식단"),
    ("기타",           "etc",                    "기타 건강 관련 정보"),
]

cat_ids = {}
print("\n카테고리 설정 중...")
for name, slug, desc in CATS:
    # 기존 확인
    r = requests.get(f"{base}/categories", auth=auth,
                    params={"slug": slug, "per_page": 1}, timeout=10)
    if r.status_code == 200 and r.json():
        cid = r.json()[0]["id"]
        cat_ids[slug] = cid
        print(f"  ✅ 기존: {name} (ID:{cid})")
    else:
        cr = requests.post(f"{base}/categories", auth=auth,
                          json={"name": name, "slug": slug, "description": desc},
                          timeout=10)
        if cr.status_code in (200, 201):
            cid = cr.json()["id"]
            cat_ids[slug] = cid
            print(f"  ✅ 생성: {name} (ID:{cid})")
        else:
            print(f"  ❌ 실패: {name} ({cr.status_code})")
    time.sleep(0.3)

# Rank Math 리디렉션 추가 (삭제된 카테고리 → 복구된 카테고리)
print("\nRank Math 리디렉션 설정...")
redirects = [
    ("/category/health-supplements/", "/category/health-supplements/"),
    ("/category/건강기능식품정보/",     "/category/health-supplements/"),
]
for src, dst in redirects:
    try:
        r2 = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": src, "comparison": "exact"}],
                "destination": dst,
                "type": 301,
                "status": "active"
            },
            timeout=10)
        print(f"  리디렉션 {src} → {dst}: {r2.status_code}")
    except:
        pass

# 색인 허용 확인
requests.post(f"{base}/settings", auth=auth,
             json={"blog_public": True}, timeout=8)
print("\n색인허용: OK")

# Google ping
try:
    sm = requests.utils.quote(f"{SITE}/sitemap_index.xml")
    requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=6)
    print("Google ping: OK")
except: pass

print(f"\n✅ k-health365.com 카테고리 5개 설정 완료!")
print(f"카테고리: {list(cat_ids.keys())}")
