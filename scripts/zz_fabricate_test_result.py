import json
import os

import requests

WP_USER = "huh0303@gmail.com"
pw = os.environ["KHEALTH365COM"]
r = requests.get(
    "https://k-health365.com/wp-json/wp/v2/posts",
    auth=(WP_USER, pw),
    params={"per_page": 1, "status": "private", "_fields": "id,link,title"},
    timeout=15,
)
posts = r.json()
print("found post:", posts)
rec = {
    "title": posts[0]["title"]["rendered"] if posts else "no post",
    "status": "draft",
    "url": posts[0]["link"] if posts else "",
}
json.dump({"records": [rec]}, open("newsroom_publish_result.json", "w"))
