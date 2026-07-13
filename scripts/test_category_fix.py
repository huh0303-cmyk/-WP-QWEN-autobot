import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, find_existing_wp_category, get_category_for_post

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")

# 실제 발행 로직과 동일하게 카테고리명 산출 후 생성 테스트
cat_name = get_category_for_post(site["theme"], "H-2 visa worker guide", "H-2 Visa Guide")
cat_id = find_existing_wp_category(site["url"], pw, cat_name)

# 실제로 그 ID가 사이트에 존재하는지 재확인
r = requests.get(f"{site['url']}/wp-json/wp/v2/categories/{cat_id}", auth=(WP_USER, pw), timeout=15)

result = {"theme": site["theme"], "resolved_category_name": cat_name, "category_id": cat_id,
          "verify_status": r.status_code, "verify_body": r.json() if r.status_code == 200 else r.text[:200]}
with open("cat_test_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
