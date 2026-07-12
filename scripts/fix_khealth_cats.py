import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM", "")

if not pw:
    print("NO PASSWORD"); exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)
print("=== health-supplements 글 원상복귀 + 색인 ===")

# 1. health-supplements 카테고리 ID 확인
r = requests.get(base + "/categories", auth=auth,
                params={"slug": "health-supplements", "per_page": 1}, timeout=10)
if r.status_code == 200 and r.json():
    cid = r.json()[0]["id"]
    print("Category ID:" + str(cid))
else:
    print("카테고리 없음 - 재생성")
    cr = requests.post(base + "/categories", auth=auth,
                      json={"name": "건강기능식품정보",
                            "slug": "health-supplements",
                            "description": "건강기능식품, 영양제, 비타민, 오메가3, 콜라겐, 프로바이오틱스 정보"},
                      timeout=10)
    cid = cr.json()["id"]
    print("Created ID:" + str(cid))

# 2. 모든 글 수집
all_posts = []
page = 1
while True:
    r2 = requests.get(base + "/posts", auth=auth,
                     params={"per_page": 100, "page": page,
                             "status": "publish",
                             "_fields": "id,title,categories,meta"},
                     timeout=20)
    if r2.status_code != 200 or not r2.json(): break
    all_posts.extend(r2.json())
    if len(r2.json()) < 100: break
    page += 1
    time.sleep(0.2)

print("Total posts:" + str(len(all_posts)))

# 3. 영양제 관련 키워드로 재배분
KW = ["오메가3","비타민","콜라겐","영양제","콘드로이친","루테인","마그네슘",
      "홍삼","프로바이오틱스","유산균","침향","알부민","코엔자임","나토키나제",
      "밀크씨슬","보스웰리아","강황","셀레늄","아연","크릴오일","NMN",
      "레스베라트롤","비오틴","철분","엽산","칼슘","프로폴리스","글루코사민",
      "히알루론산","펩타이드","CoQ10","오메가","supplement","vitamin",
      "collagen","probiotic","omega"]

assigned = already = 0
for p in all_posts:
    t     = p.get("title", {})
    title = t.get("rendered", "") if isinstance(t, dict) else str(t)
    if any(kw in title for kw in KW):
        cats = p.get("categories", [])
        if cid not in cats:
            cats.append(cid)
            requests.post(base + "/posts/" + str(p["id"]),
                         auth=auth, json={"categories": cats}, timeout=10)
            assigned += 1
            # 색인 요청
            try:
                requests.post(SITE + "/wp-json/rankmath/v1/instantIndexing",
                             auth=auth,
                             json={"urls": [SITE + "/?p=" + str(p["id"])],
                                   "action": "URL_UPDATED"}, timeout=8)
            except: pass
        else:
            already += 1

print("Newly assigned:" + str(assigned))
print("Already in category:" + str(already))

# 4. Uncategorized 글도 확인 (카테고리 없는 글)
orphan = 0
for p in all_posts:
    cats = p.get("categories", [])
    if len(cats) == 0 or (len(cats) == 1 and cats[0] == 1):  # 1 = Uncategorized
        t     = p.get("title", {})
        title = t.get("rendered", "") if isinstance(t, dict) else str(t)
        print("  ORPHAN: " + title[:50])
        orphan += 1
        if orphan >= 5: break

print("Orphan posts (no category):" + str(orphan))

# 5. 퍼머링크 재저장
for _ in range(2):
    requests.post(base + "/settings", auth=auth,
                 json={"permalink_structure": "/%postname%/",
                       "blog_public": True}, timeout=10)
    time.sleep(1)

# 6. sitemap ping
try:
    for sm_path in ["/sitemap_index.xml", "/post-sitemap1.xml",
                    "/category-sitemap.xml"]:
        enc = requests.utils.quote(SITE + sm_path)
        requests.get("https://www.google.com/ping?sitemap=" + enc, timeout=5)
        requests.get("https://www.bing.com/ping?sitemap=" + enc, timeout=5)
    print("Google/Bing ping OK")
except: pass

print("=== DONE ===")
