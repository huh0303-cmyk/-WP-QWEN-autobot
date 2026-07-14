import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://theseouljournal.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

result = {}

# 1) Elementor 템플릿(elementor_library) 목록 확인
r = requests.get(f"{base}/wp-json/wp/v2/elementor_library", auth=(WP_USER, pw),
                  params={"per_page": 50}, timeout=25)
result["elementor_library_status"] = r.status_code
result["elementor_templates"] = r.json() if r.status_code == 200 else r.text[:300]

# 2) 일반 포스트도 같은 문제인지 확인
r2 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                   params={"per_page": 1, "_fields": "id,title,link"}, timeout=20)
result["sample_post"] = r2.json() if r2.status_code == 200 else None

with open("seoul_journal_check.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
print(json.dumps(result, ensure_ascii=False, indent=2, default=str)[:3000])
