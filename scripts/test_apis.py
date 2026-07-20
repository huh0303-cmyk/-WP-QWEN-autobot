import bcrypt
import base64
import time
import requests

NAVER_CLIENT_ID = "yoin1sTxAM3nZRlNWOURG"
NAVER_CLIENT_SECRET = "$2a$04$2SMgfLZ6KshRNtu3zZBv/e"
DOMEGGOOK_API_KEY = "6158ceeaf61ef5f74464e1059c699984"


def get_naver_token():
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
