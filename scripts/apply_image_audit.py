#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_image_audit.py
─────────────────────────────────────────────────────────────
audit_image_relevance.py가 만든 image_audit_manifest.json을 읽어서,
verdict가 "MISMATCH"로 확정된 이미지만 실제로 글 본문에서 제거한다.
("UNKNOWN" - 분류 실패 - 는 오탐 방지를 위해 자동 삭제하지 않고 로그만 남김)

사이트별 WP 비밀번호(REST 쓰기 권한) 필요 — GitHub Actions에서
secrets.<SITE> 환경변수로 주입해서 실행.
"""
import os
import re
import json
import requests
from collections import defaultdict

WP_USER = "huh0303@gmail.com"
MANIFEST_PATH = "image_audit_manifest.json"

SITE_SECRET_MAP = {
    "https://k-health365.com":        "KHEALTH365COM",
    "https://koreamedicaltour.com":   "KOREAMEDICALTOURCOM",
    "https://koreainvest365.com":     "KOREAINVEST365COM",
    "https://ki-korea.com":           "KIKOREACOM",
    "https://koreainsurance365.com":  "KOREAINSURANCE365COM",
    "https://kfinance365.com":        "KFINANCE365COM",
    "https://koreataxnlaw.com":       "KOREATAXNLAWCOM",
    "https://koreacrypto365.com":     "KOREACRYPTO365COM",
    "https://krealestate365.com":     "KREALESTATE365COM",
    "https://ktech365.com":           "KTECH365COM",
    "https://kskin365.com":           "KSKIN365COM",
    "https://oliveyoungkorea.com":    "OLIVEYOUNGKOREACOM",
    "https://kworld365.com":          "KWORLD365COM",
    "https://k-trip365.com":          "KTRIP365COM",
    "https://k-visa365.com":          "KVISA365COM",
    "https://koreawedding365.com":    "KOREAWEDDING365COM",
    "https://kstudy365.com":          "KSTUDY365COM",
    "https://studyinkorea365.com":    "STUDYINKOREA365COM",
    "https://kieca-korea.org":        "KIECAKOREAORG",
    "https://ksa-korea.org":          "KSAKOREAORG",
    "https://sis-korea.com":          "SISKOREACOM",
    "https://jobkorea365.com":        "JOBKOREA365COM",
    "https://jobinkorea365.com":      "JOBINKOREA365COM",
    "https://jobkoreaglobal.com":     "JOBKOREAGLOBALCOM",
    "https://korea365.org":           "KOREA365ORG",
    "https://koreanews365.com":       "KOREANEWS365COM",
    "https://theseouljournal.com":    "THESEOULJOURNALCOM",
}


def log(msg):
    print(msg, flush=True)


def remove_image_block(content, image_url):
    pattern = re.compile(
        r'<figure\b[^>]*>(?:(?!</figure>).)*?<img[^>]+src="' + re.escape(image_url)
        + r'"[^>]*>(?:(?!</figure>).)*?</figure>\s*',
        re.IGNORECASE | re.DOTALL,
    )
    new_content, n = pattern.subn('', content)
    return new_content, n


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    mismatches = [m for m in manifest if m.get("verdict") == "MISMATCH"]
    unknowns = [m for m in manifest if m.get("verdict") == "UNKNOWN"]
    if unknowns:
        log(f"ℹ️ 분류 실패(UNKNOWN) {len(unknowns)}건은 오탐 방지를 위해 자동 삭제하지 않음 (수동 확인 필요)")

    by_post = defaultdict(list)
    for item in mismatches:
        by_post[(item["site"], item["post_id"])].append(item)

    ok = fail = skip = 0
    for (site, post_id), items in by_post.items():
        secret_name = SITE_SECRET_MAP.get(site)
        pw = os.environ.get(secret_name) if secret_name else None
        if not pw:
            log(f"[{site}#{post_id}] ⚠️ 시크릿 없음 → 건너뜀")
            skip += 1
            continue

        auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
        try:
            r = requests.get(
                f"{site}/wp-json/wp/v2/posts/{post_id}",
                auth=auth, params={"context": "edit", "_fields": "content"}, timeout=20,
            )
        except Exception as e:
            log(f"[{site}#{post_id}] ⚠️ 조회 오류: {e}")
            fail += 1
            continue
        if r.status_code != 200:
            log(f"[{site}#{post_id}] ⚠️ 조회 실패 HTTP {r.status_code}")
            fail += 1
            continue

        content_obj = r.json().get("content", {})
        content = content_obj.get("raw") or content_obj.get("rendered", "")

        removed_total = 0
        for item in items:
            content, n = remove_image_block(content, item["image_url"])
            removed_total += n

        if removed_total == 0:
            log(f"[{site}#{post_id}] ⚠️ 이미지 블록 매칭 실패 (이미 수정됐거나 구조 변경) — 건너뜀")
            skip += 1
            continue

        try:
            pr = requests.post(
                f"{site}/wp-json/wp/v2/posts/{post_id}",
                auth=auth, json={"content": content}, timeout=30,
            )
        except Exception as e:
            log(f"[{site}#{post_id}] ⚠️ 업데이트 오류: {e}")
            fail += 1
            continue

        if pr.status_code in (200, 201):
            log(f"[{site}#{post_id}] ✅ 무관 이미지 {removed_total}개 제거 완료")
            ok += 1
        else:
            log(f"[{site}#{post_id}] ⚠️ 업데이트 실패 HTTP {pr.status_code}: {pr.text[:150]}")
            fail += 1

    log("=" * 60)
    log(f"완료: 성공 {ok} / 실패 {fail} / 건너뜀 {skip} (대상 {len(by_post)}개 글, MISMATCH {len(mismatches)}건)")


if __name__ == "__main__":
    main()
