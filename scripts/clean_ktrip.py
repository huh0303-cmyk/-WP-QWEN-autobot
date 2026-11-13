import os, requests, time, re

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-trip365.com"
pw      = os.getenv("KTRIP365COM", "")
base    = SITE + "/wp-json/wp/v2"
auth    = (WP_USER, pw)

print("=== k-trip365 cleanup + hero image ===")

DUMMY = ["hello world","sample page","lorem ipsum","welcome to wordpress","test post","untitled"]
KOREA = ["korea","korean","seoul","busan","jeju","incheon","hotel","travel","trip","tour",
         "food","restaurant","cafe","temple","palace","hiking","beach","island","transport",
         "subway","ktx","visa","market","shop","spring","summer","autumn","winter","cherry",
         "stay","hostel","airbnb","guesthouse","pension","resort","attraction","tourist"]

# 1. 전체 글 수집
all_posts = []
page = 1
while True:
    r = requests.get(base + "/posts", auth=auth,
                    params={"per_page":100,"page":page,"status":"publish",
                            "_fields":"id,title,content"}, timeout=20)
    if r.status_code != 200 or not r.json(): break
    all_posts.extend(r.json())
    if len(r.json()) < 100: break
    page += 1
    time.sleep(0.2)

print("Total: " + str(len(all_posts)))

keep = delete = 0
for p in all_posts:
    t     = p.get("title",{})
    title = re.sub("<[^>]+>","", t.get("rendered","") if isinstance(t,dict) else str(t)).strip().lower()
    c     = p.get("content",{})
    body  = re.sub("<[^>]+>","", c.get("rendered","") if isinstance(c,dict) else str(c))
    blen  = len(body.replace(" ","").replace("\n",""))

    bad = any(d in title for d in DUMMY) or blen < 300
    if not bad:
        has_korea = any(kw in title or kw in body.lower() for kw in KOREA)
        if not has_korea: bad = True

    if bad and os.getenv("KTRIP_ALLOW_DELETION", "false").lower() == "true":
        dr = requests.delete(base+"/posts/"+str(p["id"]), auth=auth,
                            params={"force":True}, timeout=10)
        if dr.status_code in (200,201):
            delete += 1
            print("DEL: " + title[:60])
        time.sleep(0.2)
    else:
        keep += 1

print("Keep:" + str(keep) + " Deleted:" + str(delete))

# 2. SAFETY: Never assign one shared hero image to multiple posts.
# This script previously uploaded one Pixabay image and assigned the same media ID
# to every recent post missing featured_media. That caused visible duplicates.
# Image repairs must use a per-post topic-specific selection with a persistent
# uniqueness ledger and must verify each media ID before updating WordPress.
print("Shared hero image backfill disabled: prevents duplicate featured images")

# 3. Google ping
try:
    sm = requests.utils.quote(SITE+"/sitemap_index.xml")
    requests.get("https://www.google.com/ping?sitemap="+sm, timeout=6)
    print("Ping OK")
except: pass

print("=== DONE ===")
