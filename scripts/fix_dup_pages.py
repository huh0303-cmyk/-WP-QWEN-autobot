import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

log = []


def get_pw(site_url):
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    return os.getenv(site["wp_pass_env"], "")


# 1) jobinkorea365.com: privacy-policy-2(395) 삭제, privacy-policy(408) 유지
pw = get_pw("https://jobinkorea365.com")
r = requests.delete("https://jobinkorea365.com/wp-json/wp/v2/pages/395",
                     auth=(WP_USER, pw), params={"force": "true"}, timeout=20)
log.append({"site": "jobinkorea365.com", "action": "delete dup id395", "status": r.status_code})

# 2) jobkoreaglobal.com: privacy-policy-2(646) 삭제, privacy-policy(659) 유지
pw = get_pw("https://jobkoreaglobal.com")
r = requests.delete("https://jobkoreaglobal.com/wp-json/wp/v2/pages/646",
                     auth=(WP_USER, pw), params={"force": "true"}, timeout=20)
log.append({"site": "jobkoreaglobal.com", "action": "delete dup id646", "status": r.status_code})

# 3) jobkorea365.com: privacy-policy-2(385)의 슬러그를 정상 privacy-policy로 변경
pw = get_pw("https://jobkorea365.com")
r = requests.patch("https://jobkorea365.com/wp-json/wp/v2/pages/385",
                    auth=(WP_USER, pw), json={"slug": "privacy-policy"}, timeout=20)
new_link = r.json().get("link") if r.status_code in (200, 201) else None
log.append({"site": "jobkorea365.com", "action": "rename slug id385", "status": r.status_code, "new_link": new_link})

with open("fix_dup_pages_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
