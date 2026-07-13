import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")

r = requests.get(f"{site['url']}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                  params={"per_page": 100}, timeout=20)
cats = r.json()
result = [{"id": c["id"], "name": c["name"], "count": c["count"]} for c in cats]

# 방금 테스트로 만든 빈 카테고리(count=0, 이름이 Foreign Worker Recruitment) 삭제
deleted = []
for c in cats:
    if c["name"] == "Foreign Worker Recruitment" and c["count"] == 0:
        dr = requests.delete(f"{site['url']}/wp-json/wp/v2/categories/{c['id']}",
                              auth=(WP_USER, pw), params={"force": "true"}, timeout=15)
        deleted.append({"id": c["id"], "name": c["name"], "status": dr.status_code})

with open("cats_check.json", "w", encoding="utf-8") as f:
    json.dump({"categories": result, "deleted_test_cat": deleted}, f, ensure_ascii=False, indent=2)
print(json.dumps({"categories": result, "deleted_test_cat": deleted}, ensure_ascii=False, indent=2))
