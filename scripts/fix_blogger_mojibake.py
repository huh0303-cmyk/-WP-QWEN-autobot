import os
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
blog_id = "4456888951628869767"
post_id = "3175985090528812889"
r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}", headers=auth, timeout=20)
data = r.json()
content = data.get("content", "")

count = content.count('�')
print("mojibake char occurrences:", count)

fixed = content.replace('마�찰', '마찰')
remaining = fixed.count('�')
print("remaining after targeted fix:", remaining)
if remaining:
    # Print context for anything not covered by the known pattern, and fail
    # loudly rather than guess at other words.
    idx = fixed.find('�')
    print("UNHANDLED CONTEXT:", repr(fixed[max(0, idx-100):idx+100]))
    raise SystemExit("unhandled mojibake pattern; not applying a blind global replace")

if fixed == content:
    print("no change needed")
else:
    patch = requests.patch(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}",
                            headers=auth, json={"content": fixed}, timeout=30)
    patch.raise_for_status()
    print("patched successfully, status:", patch.status_code)
