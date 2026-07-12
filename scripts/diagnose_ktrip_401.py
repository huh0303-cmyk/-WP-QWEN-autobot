# -*- coding: utf-8 -*-
"""k-trip365.com 401 오류 원인 진단 (임시)."""
import os, json, requests

WP_USER = "huh0303@gmail.com"
SITE = "https://k-trip365.com"
pw = os.getenv("KTRIP365COM", "")

result = {"site": SITE, "wp_user": WP_USER, "has_password_secret": bool(pw)}

# 1) REST API 자체가 살아있는지 (인증 없이)
try:
    r = requests.get(f"{SITE}/wp-json/", timeout=15)
    result["rest_api_root_status"] = r.status_code
except Exception as e:
    result["rest_api_root_status"] = f"오류: {e}"

# 2) 저장된 Application Password로 "나는 누구인가" 확인
if pw:
    try:
        r = requests.get(f"{SITE}/wp-json/wp/v2/users/me", auth=(WP_USER, pw), timeout=15)
        result["auth_me_status"] = r.status_code
        try:
            result["auth_me_body"] = r.json()
        except Exception:
            result["auth_me_body"] = r.text[:300]
    except Exception as e:
        result["auth_me_status"] = f"오류: {e}"

# 3) 글 목록 조회 (인증 없이도 공개글은 보통 보임 - 사이트 자체 생존 확인)
try:
    r = requests.get(f"{SITE}/wp-json/wp/v2/posts", params={"per_page": 1}, timeout=15)
    result["public_posts_status"] = r.status_code
except Exception as e:
    result["public_posts_status"] = f"오류: {e}"

with open("verify_ktrip_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
