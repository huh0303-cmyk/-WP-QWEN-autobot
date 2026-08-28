#!/usr/bin/env python3
"""Verify Blogger OAuth and list blogs available to the configured Google account."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from process_platform_queue import _access_token


def main():
    profile = os.environ.get("AUTH_PROFILE", "")
    token = _access_token(profile)
    if not token:
        raise SystemExit("Blogger OAuth 자격증명이 없습니다.")
    response = requests.get(
        "https://www.googleapis.com/blogger/v3/users/self/blogs",
        headers={"Authorization": f"Bearer {token}"}, timeout=30,
    )
    if response.status_code != 200:
        raise SystemExit(f"Blogger OAuth 확인 실패 HTTP {response.status_code}: {response.text[:500]}")
    blogs = [{"id": str(item.get("id", "")), "name": item.get("name", ""), "url": item.get("url", "")} for item in response.json().get("items", [])]
    print(json.dumps({"ok": True, "count": len(blogs), "blogs": blogs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
