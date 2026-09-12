import os
import requests

SITE = "https://k-health365.com"
AUTH = ("huh0303@gmail.com", os.environ["KHEALTH365COM"])
POST_ID = 6004
# Recovered from the post's own URL slug (generated correctly at publish time,
# before whatever encoding step corrupted the stored title/content).
RECOVERED_TITLE = "건강검진 대상 조회 전 확인할 네 가지"

r = requests.get(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth=AUTH,
                  params={"_fields": "id,status,title,content"}, timeout=20)
r.raise_for_status()
data = r.json()
print("current status:", data.get("status"))
print("current title (garbled):", data.get("title", {}).get("rendered"))

# The body itself (105 chars, also garbled) has no recoverable source the way
# the title does via its slug — that needs real content, not a mechanical
# fix, so this only repairs the title and takes the post out of public view
# rather than leaving unusable garbled text live.
update = requests.post(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth=AUTH, timeout=20,
                        json={"title": RECOVERED_TITLE, "status": "draft"})
update.raise_for_status()
print("updated:", update.status_code, update.json().get("status"))
