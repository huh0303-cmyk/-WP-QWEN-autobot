import os, requests, time, re

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-trip365.com"
pw      = os.getenv("KTRIP365COM", "")

if not pw:
    print("NO PASSWORD")
    exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)

print("k-trip365 cleanup start")

DUMMY = ["hello world","sample page","lorem ipsum","welcome to wordpress",
         "test post","untitled","just another"]

KOREA = ["korea","korean","seoul","busan","jeju","incheon","hotel","travel",
         "trip","tour","food","restaurant","cafe","temple","palace","hiking",
         "beach","island","transport","subway","ktx","visa","market","shop",
         "spring","summer","autumn","winter","cherry","stay","hostel","airbnb",
         "guesthouse","pension","resort","attraction","tourist","itinerary"]

all_posts = []
page = 1
while True:
    r = requests.get(base + "/posts", auth=auth,
                    params={"per_page": 100, "page": page,
                            "status": "publish",
                            "_fields": "id,title,content"},
                    timeout=20)
    if r.status_code != 200 or not r.json():
        break
    all_posts.extend(r.json())
    if len(r.json()) < 100:
        break
    page += 1
    time.sleep(0.2)

print("Total posts: " + str(len(all_posts)))

keep = delete = 0
for p in all_posts:
    t     = p.get("title", {})
    title = re.sub("<[^>]+>", "",
            t.get("rendered","") if isinstance(t,dict) else str(t)).strip().lower()
    c     = p.get("content", {})
    body  = re.sub("<[^>]+>", "",
            c.get("rendered","") if isinstance(c,dict) else str(c))
    body_clean = body.replace(" ","").replace("\n","")

    bad = False

    # 1. dummy pattern
    for d in DUMMY:
        if d in title:
            bad = True
            break

    # 2. too short
    if len(body_clean) < 300:
        bad = True

    # 3. no Korea keyword
    if not bad:
        has_korea = any(kw in title or kw in body.lower() for kw in KOREA)
        if not has_korea:
            bad = True

    if bad:
        dr = requests.delete(base + "/posts/" + str(p["id"]),
                            auth=auth, params={"force": True}, timeout=10)
        if dr.status_code in (200, 201):
            delete += 1
            print("DEL: " + title[:60])
        time.sleep(0.2)
    else:
        keep += 1

print("Keep: " + str(keep))
print("Deleted: " + str(delete))

try:
    sm = requests.utils.quote(SITE + "/sitemap_index.xml")
    requests.get("https://www.google.com/ping?sitemap=" + sm, timeout=6)
    print("Ping OK")
except:
    pass

print("DONE")
