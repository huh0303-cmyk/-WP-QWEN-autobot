import os
import requests

SITE = "https://kfinance365.com"
AUTH = ("huh0303@gmail.com", os.environ["KFINANCE365COM"])

r = requests.get(f"{SITE}/wp-json/wp/v2/menus", auth=AUTH, timeout=20)
print("menus status:", r.status_code)
print(r.json())

menus = r.json()
if isinstance(menus, list):
    for m in menus:
        print("menu:", m.get("id"), m.get("name"), m.get("locations"))

r2 = requests.get(f"{SITE}/wp-json/wp/v2/menu-items", auth=AUTH, params={"per_page": 100}, timeout=20)
print("menu-items status:", r2.status_code)
items = r2.json()
if isinstance(items, list):
    for it in items:
        print(it.get("id"), it.get("title", {}).get("rendered"), it.get("url"), it.get("menus"), it.get("object"), it.get("object_id"))
else:
    print(items)
