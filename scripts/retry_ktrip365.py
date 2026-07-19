#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k-trip365.com 전용 - 느린 서버 대응 45초 타임아웃 + 재시도"""
import os, re, html as _html
import requests
from requests.adapters import HTTPAdapter, Retry

WP_USER = "huh0303@gmail.com"
URL = "https://k-trip365.com"
PW = os.getenv("KTRIP365COM", "")

session = requests.Session()
retries = Retry(total=4, backoff_factor=2, status_forcelist=[502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))


def auth():
    return requests.auth.HTTPBasicAuth(WP_USER, PW)


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


def main():
    lines = []
    def log(m):
        print(m)
        lines.append(m)

    if not PW:
        log("NO PASSWORD")
        return

    filled = 0
    page = 1
    while True:
        r = session.get(f"{URL}/wp-json/wp/v2/posts", auth=auth(),
                         params={"per_page": 100, "page": page, "status": "publish",
                                 "_fields": "id,title,meta"}, timeout=45)
        if r.status_code != 200:
            log(f"목록 조회 실패 page={page} status={r.status_code}")
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            meta = p.get("meta", {}) or {}
            kw = meta.get("rank_math_focus_keyword", "")
            if kw and str(kw).strip():
                continue
            title = _html.unescape(strip_tags(p.get("title", {}).get("rendered", "")))
            new_kw = title[:60]
            try:
                rr = session.post(f"{URL}/wp-json/wp/v2/posts/{p['id']}", auth=auth(),
                                   json={"meta": {"rank_math_focus_keyword": new_kw}}, timeout=45)
                if rr.status_code in (200, 201):
                    filled += 1
                    log(f"  ✅ [{p['id']}] 키워드 채움: {new_kw[:40]}")
                else:
                    log(f"  ⚠️ [{p['id']}] 실패 status={rr.status_code}")
            except Exception as e:
                log(f"  ⚠️ [{p['id']}] 오류: {e}")
        if len(batch) < 100:
            break
        page += 1

    log(f"\n완료: {filled}건 채움")
    with open("fix_ktrip365_retry_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
