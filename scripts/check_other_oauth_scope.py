import os
import requests

r = requests.post(
    "https://oauth2.googleapis.com/token",
    data={
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    },
    timeout=20,
)
print("status:", r.status_code)
print("scope:", r.json().get("scope"))
