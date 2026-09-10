#!/usr/bin/env python3
"""One-off, user-approved: remove off-topic general-health posts from
k-health365-edu (K-Medical Job Center), whose declared scope is Korean
medical/care/welfare *qualification and employment* content, not general
health/symptom articles. Root cause fixed separately in PR #89 (medical
editorial rules were never reaching the GPT writer prompt in
scripts/auto_write_and_draft.py)."""
import os
import requests

BLOG_ID = "3205814823967421343"
OFFTOPIC_POST_IDS = [
    "3732024823098017590",  # carpal tunnel syndrome symptoms article
    "6365180926113839498",  # general daily health management article
    "1013819989643376872",  # general preventive medicine article
]


def access_token():
    refresh_token = os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"]
    client_id = os.environ["BLOGGER_GOOGLE_CLIENT_ID"]
    client_secret = os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"]
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


token = access_token()
headers = {"Authorization": f"Bearer {token}"}
for post_id in OFFTOPIC_POST_IDS:
    r = requests.delete(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/{post_id}",
        headers=headers, timeout=30,
    )
    print(post_id, "delete status:", r.status_code, r.text[:200] if r.text else "")
