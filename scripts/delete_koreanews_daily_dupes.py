#!/usr/bin/env python3
"""One-off, user-approved: koreanews365daily.blogspot.com's only WP source
post during a Hostinger rate-limit outage (2026-09-01 to 2026-09-09) was a
single "how to read the news" meta-article, so every scheduled Blogger
rewrite in that window reused the same source and produced four
near-identical off-topic posts. Delete all four; the underlying WP outage
is being fixed separately (rss_watch.py dispatch pacing)."""
import os
import requests

BLOG_ID = "7521251102691129954"  # koreanews365daily.blogspot.com
OFFTOPIC_POST_IDS = [
    "1500050473572618123",  # 우선 확인 네 가지
    "1725516656336654338",  # 한국 뉴스·시사 보도의 원칙과 독자의 확인 지침
    "4575495679057619616",  # 저출산·고령화 (also off-topic: general policy essay, not news)
    "1584864750010096023",  # 독자 질문으로 본 한국 시사: 단계별 뉴스 검증법
]


def access_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
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
