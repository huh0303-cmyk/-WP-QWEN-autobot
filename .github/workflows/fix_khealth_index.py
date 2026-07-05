import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE = "https://k-health365.com"
pw = os.getenv("KHEALTH365COM","")

if not pw:
    print("NO PASSWORD")
    exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=== k-health365.com index fix ===")

# 1. 현재 설정 확인
r = requests.get(base + "/settings", auth=auth, timeout=10)
s = r.json()
print("URL:", s.get("url",""))
print("blog_public:", s.get("blog_public",""))

# 2. blog_public 강제 True
r2 = requests.post(base + "/settings", auth=auth,
                  json={"blog_public": True,
                        "url": SITE,
                        "home": SITE}, timeout=10)
print("blog_public fix:", r2.status_code)

# 3. noindex 글 전부 수정
print("scanning noindex posts...")
page = 1
fixed = 0
while True:
    r3 = requests.get(base + "/posts", auth=auth,
                     params={"per_page":100,"page":page,
                             "status":"publish","_fields":"id,meta"},
                     timeout=20)
    if r3.status_code != 200 or not r3.json():
        break
    posts = r3.json()
    for p in posts:
        meta = p.get("meta",{})
        if isinstance(meta, dict):
            robots = str(meta.get("rank_math_robots","")).lower()
            if "noindex" in robots:
                requests.post(base + "/posts/" + str(p["id"]),
                             auth=auth,
                             json={"meta":{"rank_math_robots":["index","follow"]}},
                             timeout=10)
                fixed += 1
    if len(posts) < 100:
        break
    page += 1
    time.sleep(0.3)

print("noindex fixed:", fixed)

# 4. 퍼머링크 재저장 3회
for _ in range(3):
    requests.post(base + "/settings", auth=auth,
                 json={"permalink_structure": "/%postname%/"}, timeout=10)
    time.sleep(1)
print("permalink resaved")

# 5. Google/Bing ping
for sm in ["/sitemap_index.xml", "/post-sitemap.xml"]:
    try:
        enc = requests.utils.quote(SITE + sm)
        requests.get("https://www.google.com/ping?sitemap=" + enc, timeout=6)
        requests.get("https://www.bing.com/ping?sitemap=" + enc, timeout=6)
    except:
        pass
print("Google/Bing ping: done")

# 6. Rank Math Instant Indexing
try:
    r5 = requests.post(SITE + "/wp-json/rankmath/v1/instantIndexing",
                      auth=auth,
                      json={"urls":[SITE],"action":"URL_UPDATED"},
                      timeout=10)
    print("Instant Indexing:", r5.status_code)
except:
    pass

print("=== DONE ===")
