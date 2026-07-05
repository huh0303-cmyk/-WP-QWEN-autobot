import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM", "")

if not pw:
    print("NO PASSWORD"); exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)
print("=== health-supplements 카테고리 복구 ===")

# 1. 휴지통 카테고리 복구 시도
# 삭제된 카테고리는 WP REST API로 직접 복구 불가 → 재생성
r = requests.get(base + "/categories", auth=auth,
                params={"slug": "health-supplements", "per_page": 1}, timeout=10)

if r.status_code == 200 and r.json():
    cid = r.json()[0]["id"]
    print("EXISTS slug=health-supplements ID:" + str(cid))
else:
    cr = requests.post(base + "/categories", auth=auth,
                      json={
                          "name":        "건강기능식품정보",
                          "slug":        "health-supplements",
                          "description": "건강기능식품, 영양제, 비타민, 오메가3, 콜라겐, 프로바이오틱스 정보"
                      }, timeout=10)
    if cr.status_code in (200, 201):
        cid = cr.json()["id"]
        print("CREATED ID:" + str(cid))
    else:
        print("FAIL " + str(cr.status_code) + " " + cr.text[:100])
        exit(1)

# 2. 영양제 관련 글 재배분
KW = ["오메가3","비타민","콜라겐","영양제","콘드로이친","루테인","마그네슘",
      "홍삼","프로바이오틱스","유산균","침향","알부민","코엔자임","나토키나제",
      "밀크씨슬","보스웰리아","강황","셀레늄","아연","크릴오일","NMN",
      "레스베라트롤","비오틴","철분","엽산","칼슘","오메가","프로폴리스",
      "vitamin","supplement","collagen","probiotic","omega"]

page = 1
assigned = 0
while True:
    r2 = requests.get(base + "/posts", auth=auth,
                     params={"per_page": 100, "page": page,
                             "status": "publish",
                             "_fields": "id,title,categories"}, timeout=20)
    if r2.status_code != 200 or not r2.json(): break
    posts = r2.json()
    for p in posts:
        t     = p.get("title", {})
        title = t.get("rendered", "") if isinstance(t, dict) else str(t)
        if any(kw in title for kw in KW):
            cats = p.get("categories", [])
            if cid not in cats:
                cats.append(cid)
                requests.post(base + "/posts/" + str(p["id"]),
                             auth=auth, json={"categories": cats}, timeout=10)
                assigned += 1
    if len(posts) < 100: break
    page += 1
    time.sleep(0.3)

print("Assigned " + str(assigned) + " posts to health-supplements")

# 3. 퍼머링크 재저장 (카테고리 URL 살리기)
for _ in range(3):
    requests.post(base + "/settings", auth=auth,
                 json={"permalink_structure": "/%postname%/"}, timeout=10)
    time.sleep(1)
print("Permalink resaved")

# 4. Google ping
try:
    sm = requests.utils.quote(SITE + "/sitemap_index.xml")
    requests.get("https://www.google.com/ping?sitemap=" + sm, timeout=6)
    print("Google ping OK")
except: pass

print("=== DONE: /category/health-supplements/ 복구 완료 ===")
