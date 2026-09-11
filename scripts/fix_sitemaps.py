import os, requests, time, re, html

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-trip365.com"
pw      = os.getenv("KTRIP365COM", "")

if not pw:
    print("NO PASSWORD"); exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=== k-trip365.com 더미글 삭제 시작 ===")

# 삭제 대상 패턴
DUMMY_PATTERNS = [
    r"hello world",
    r"sample page",
    r"lorem ipsum",
    r"this is an example",
    r"welcome to wordpress",
    r"just another wordpress",
    r"test post",
    r"draft",
    r"untitled",
    r"^sample",
    r"^test",
]

# 한국 관련 키워드 (이것 없으면 삭제 후보)
KOREA_KEYWORDS = [
    "korea","korean","seoul","busan","jeju","incheon","gangnam","hongdae",
    "hanok","temple","palace","dmz","kpop","k-pop","hallyu","hansik",
    "bibimbap","bulgogi","kimchi","tteokbokki","samgyeopsal","galbi",
    "hotel","hostel","airbnb","pension","resort","guesthouse",
    "travel","trip","tour","visit","itinerary","tourist","attraction",
    "subway","ktx","bus","transport","flight","airport",
    "restaurant","cafe","food","eat","drink","market","shopping",
    "visa","foreigner","expat","tourist","currency","won",
    "spring","summer","autumn","fall","winter","cherry blossom",
    "hiking","mountain","beach","island","nature","park",
    "한국","서울","부산","제주","여행","관광","호텔","맛집","음식",
    "숙소","교통","지하철","버스","공항","펜션","리조트",
]

# 전체 글 수집
all_posts = []
page = 1
while True:
    r = requests.get(base + "/posts", auth=auth,
                    params={"per_page":100,"page":page,
                            "status":"publish",
                            "_fields":"id,title,content,date"},
                    timeout=20)
    if r.status_code != 200 or not r.json(): break
    all_posts.extend(r.json())
    if len(r.json()) < 100: break
    page += 1
    time.sleep(0.2)

print(f"총 글 수: {len(all_posts)}")

keep = delete = 0
deleted_titles = []

for p in all_posts:
    t     = p.get("title",{})
    title = html.unescape(re.sub('<[^>]+>','',
            t.get("rendered","") if isinstance(t,dict) else str(t))).strip()
    c     = p.get("content",{})
    body  = re.sub('<[^>]+>','',
            c.get("rendered","") if isinstance(c,dict) else str(c))
    body_len = len(body.replace(' ','').replace('\n',''))

    title_lower = title.lower()
    body_lower  = body.lower()

    should_delete = False

    # 1. 더미 패턴 매칭
    for pat in DUMMY_PATTERNS:
        if re.search(pat, title_lower):
            should_delete = True
            break

    # 2. 본문 너무 짧음 (300자 미만)
    if body_len < 300:
        should_delete = True

    # 3. 한국 관련 키워드 전혀 없음
    if not should_delete:
        has_korea = any(kw in title_lower or kw in body_lower
                       for kw in KOREA_KEYWORDS)
        if not has_korea:
            should_delete = True

    if should_delete:
        dr = requests.delete(base + "/posts/" + str(p["id"]),
                            auth=auth,
                            params={"force": True}, timeout=10)
        if dr.status_code in (200,201):
            delete += 1
            deleted_titles.append(title[:50])
        time.sleep(0.2)
    else:
        keep += 1

print(f"\n유지: {keep}건")
print(f"삭제: {delete}건")
print(f"\n삭제된 글 목록 (처음 20개):")
for t in deleted_titles[:20]:
    print(f"  - {t}")

# Google ping
try:
    sm = requests.utils.quote(SITE + "/sitemap_index.xml")
    requests.get("https://www.google.com/ping?sitemap=" + sm, timeout=6)
    print("\nGoogle ping OK")
except: pass

print("=== 완료 ===")
