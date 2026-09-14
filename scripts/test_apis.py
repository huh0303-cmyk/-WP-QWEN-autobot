import bcrypt
import base64
import os
import time
import requests

NAVER_CLIENT_ID = os.environ.get("NAVER_COMMERCE_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.environ.get("NAVER_COMMERCE_CLIENT_SECRET", "").strip()
DOMEGGOOK_API_KEY = os.environ.get("DOMEGGOOK_API_KEY", "").strip()


def get_naver_token():
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_COMMERCE_CLIENT_ID and NAVER_COMMERCE_CLIENT_SECRET are required")
    timestamp = str(int(time.time() * 1000))
    password = f"{NAVER_CLIENT_ID}_{timestamp}"
    hashed = bcrypt.hashpw(password.encode("utf-8"), NAVER_CLIENT_SECRET.encode("utf-8"))
    signature = base64.standard_b64encode(hashed).decode("utf-8")

    resp = requests.post(
        "https://api.commerce.naver.com/external/v1/oauth2/token",
        data={
            "client_id": NAVER_CLIENT_ID,
            "timestamp": timestamp,
            "grant_type": "client_credentials",
            "client_secret_sign": signature,
            "type": "SELF",
        },
        timeout=15,
    )
    print("네이버 토큰 발급 status:", resp.status_code)
    print(resp.text[:1000])
    return resp


def test_domeggook():
    if not DOMEGGOOK_API_KEY:
        raise RuntimeError("DOMEGGOOK_API_KEY is required")
    resp = requests.get(
        "https://domeggook.com/ssl/api/",
        params={
            "ver": "4.1", "mode": "getItemList", "aid": DOMEGGOOK_API_KEY,
            "market": "dome", "om": "json", "kw": "건강기능식품", "sz": 5, "pg": 1, "so": "rd",
        },
        timeout=15,
    )
    print("도매매 API status:", resp.status_code)
    print(resp.text[:1000])


if __name__ == "__main__":
    print("=== 네이버 커머스API 테스트 ===")
    get_naver_token()
    print("\n=== 도매매 API 테스트 ===")
    test_domeggook()
