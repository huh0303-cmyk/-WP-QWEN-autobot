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

    if bad:
        dr = requests.delete(base+"/posts/"+str(p["id"]), auth=auth,
                            params={"force":True}, timeout=10)
        if dr.status_code in (200,201):
            delete += 1
            print("DEL: " + title[:60])
        time.sleep(0.2)
    else:
        keep += 1

print("Keep:" + str(keep) + " Deleted:" + str(delete))

# 2. Pixabay 한국 사진
PIXABAY_KEY = "48405185-db4f0c77ac28099db1d63de37"
photo_url = None
for q in ["Gyeongbokgung Palace Seoul Korea","Korean temple Korea","Jeju island Korea travel"]:
    try:
        r2 = requests.get("https://pixabay.com/api/",
                         params={"key":PIXABAY_KEY,"q":q,"image_type":"photo",
                                 "orientation":"horizontal","min_width":1280,
                                 "per_page":3,"safesearch":"true"}, timeout=10)
        hits = r2.json().get("hits",[])
        if hits:
            photo_url = hits[0]["largeImageURL"]
            print("Photo found: " + q)
            break
    except: pass

if photo_url:
    img_data = requests.get(photo_url, timeout=20).content
    print("Downloaded: " + str(len(img_data)) + " bytes")
    files = {"file": ("korea-hero.jpg", img_data, "image/jpeg")}
    r3 = requests.post(base+"/media", auth=auth, files=files,
                      data={"title":"Korea Travel Hero",
                            "alt_text":"Korea travel guide - Gyeongbokgung Palace Seoul"},
                      timeout=30)
    if r3.status_code in (200,201):
        media_id  = r3.json()["id"]
        media_url = r3.json()["source_url"]
        print("Uploaded media ID: " + str(media_id))
        print("URL: " + media_url)
        # 최신 글에 대표이미지 설정
        r4 = requests.get(base+"/posts", auth=auth,
                         params={"per_page":10,"status":"publish",
                                 "_fields":"id,featured_media"}, timeout=10)
        for post in r4.json():
            if not post.get("featured_media"):
                requests.post(base+"/posts/"+str(post["id"]), auth=auth,
                             json={"featured_media":media_id}, timeout=10)
                print("Featured set: post " + str(post["id"]))
                time.sleep(0.2)
    else:
        print("Upload failed: " + str(r3.status_code))
else:
    print("No photo found")

# 3. Google ping
try:
    sm = requests.utils.quote(SITE+"/sitemap_index.xml")
    requests.get("https://www.google.com/ping?sitemap="+sm, timeout=6)
    print("Ping OK")
except: pass

print("=== DONE ===")
