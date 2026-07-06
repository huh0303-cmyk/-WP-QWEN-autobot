import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-trip365.com"
pw      = os.getenv("KTRIP365COM", "")

if not pw:
    print("NO PASSWORD"); exit(1)

base = SITE + "/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=== k-trip365 hero image set ===")

# Pixabay - Korea travel photos
PIXABAY_KEY = "48405185-db4f0c77ac28099db1d63de37"

queries = [
    "Gyeongbokgung Palace Seoul Korea",
    "Korean temple roof Korea",
    "Bulguksa temple Gyeongju Korea",
    "Seoul cityscape Korea travel",
    "Jeju island Korea",
]

photo_url = None
for q in queries:
    try:
        r = requests.get("https://pixabay.com/api/",
                        params={"key": PIXABAY_KEY, "q": q,
                                "image_type": "photo", "orientation": "horizontal",
                                "min_width": 1280, "per_page": 5,
                                "safesearch": "true", "category": "travel"},
                        timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            photo_url = hits[0]["largeImageURL"]
            print("Found: " + q)
            break
    except: pass

if not photo_url:
    print("No photo - using Pexels")
    # Pexels fallback
    try:
        r2 = requests.get("https://api.pexels.com/v1/search",
                         params={"query": "Gyeongbokgung Seoul Korea temple",
                                 "per_page": 1, "orientation": "landscape"},
                         headers={"Authorization": "563492ad6f91700001000001b8e5f1a2b4e14b9a9b3c7d6e8f0a1b2c"},
                         timeout=10)
        if r2.status_code == 200:
            photos = r2.json().get("photos", [])
            if photos:
                photo_url = photos[0]["src"]["large2x"]
                print("Pexels found")
    except: pass

if not photo_url:
    print("No photo found - exit")
    exit(1)

# Download image
img_data = requests.get(photo_url, timeout=20).content
print("Downloaded: " + str(len(img_data)) + " bytes")

# Upload to WP media library
files = {"file": ("korea-travel-hero.jpg", img_data, "image/jpeg")}
r3 = requests.post(base + "/media", auth=auth, files=files,
                  data={"title": "Korea Travel Hero - Gyeongbokgung",
                        "alt_text": "Korea travel guide - Gyeongbokgung Palace Seoul"},
                  timeout=30)

if r3.status_code not in (200, 201):
    print("Upload failed: " + str(r3.status_code))
    exit(1)

media_id  = r3.json()["id"]
media_url = r3.json()["source_url"]
print("Uploaded media ID: " + str(media_id))
print("URL: " + media_url)

# Set as featured image for recent posts
r4 = requests.get(base + "/posts", auth=auth,
                 params={"per_page": 10, "status": "publish",
                         "_fields": "id,title,featured_media"}, timeout=10)

if r4.status_code == 200:
    for post in r4.json():
        if not post.get("featured_media"):
            pid = post["id"]
            requests.post(base + "/posts/" + str(pid), auth=auth,
                         json={"featured_media": media_id}, timeout=10)
            print("Set featured: post " + str(pid))
            time.sleep(0.2)

# Set site header custom image via WP settings
try:
    requests.post(base + "/settings", auth=auth,
                 json={"custom_header_image": media_url}, timeout=8)
except: pass

# Rank Math OG image
try:
    requests.post(SITE + "/wp-json/rankmath/v1/updateSettings", auth=auth,
                 json={"og_image_id": str(media_id)}, timeout=8)
    print("RankMath OG image set")
except: pass

print("=== DONE ===")
print("Korea hero image set! Media ID: " + str(media_id))
print("Image URL: " + media_url)
