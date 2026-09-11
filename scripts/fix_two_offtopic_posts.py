#!/usr/bin/env python3
"""One-off, user-approved: remove two confirmed off-topic Blogger posts found
during a 33-site editorial audit.
- korea-life-support365: a journalism fact-checking procedure manual was
  published instead of reader-facing life-support/benefits content.
- koreainsurance365: a B2B cyber-risk-for-insurers article was published on a
  consumer-facing "how to get insurance in Korea" blog."""
import os
import requests

TARGETS = [
    ("2531035487222435079", "6618632287526206705"),  # korea-life-support365
    ("8888982369193041814", "7888263532663671553"),  # koreainsurance365
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
for blog_id, post_id in TARGETS:
    r = requests.delete(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}",
        headers=headers, timeout=30,
    )
    print(blog_id, post_id, "delete status:", r.status_code, r.text[:200] if r.text else "")
