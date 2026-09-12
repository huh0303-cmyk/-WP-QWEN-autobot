import os
import re
import requests

def access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

auth = {"Authorization": f"Bearer {access_token()}"}
blog_id = "4456888951628869767"  # glow.k-health365.com per content_engine_profiles
post_id = "3175985090528812889"
r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}", headers=auth, timeout=20)
data = r.json()
content = data.get("content", "")
plain = re.sub('<[^<]+?>', ' ', content)
idx = plain.find('�')
print("title:", data.get("title"))
print("content length:", len(content))
print("first mojibake at plain-text index:", idx)
print("context:", repr(plain[max(0,idx-200):idx+200]))
