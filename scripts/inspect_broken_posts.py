import os
import requests

SITE = "https://koreamedicaltour.com"
AUTH = ("huh0303@gmail.com", os.environ["KOREAMEDICALTOURCOM"])

for pid in (1720, 1718, 637):
    r = requests.get(f"{SITE}/wp-json/wp/v2/posts/{pid}", auth=AUTH,
                      params={"_fields": "id,title,content,slug,status,excerpt"}, timeout=20)
    data = r.json()
    print("=== POST", pid, "===")
    print("status:", data.get("status"))
    print("title raw:", repr(data.get("title", {}).get("raw", data.get("title"))))
    print("slug:", data.get("slug"))
    content = data.get("content", {}).get("raw", data.get("content", {}).get("rendered", ""))
    print("content start:", repr(content[:400]))
    print()
