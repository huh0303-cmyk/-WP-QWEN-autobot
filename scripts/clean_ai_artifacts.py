#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_ai_artifacts.py
─────────────────────────────────────────────────────────────
scan_ai_artifacts.py가 만든 ai_artifact_manifest.json을 읽어서,
실제 글 본문에서 AI 흔적(프롬프트 지시문 echo, "body HTML" 라벨,
FAQ_START/END 잔재, AI 디스클레이머 문장 등)을 제거하고 발행 글을 갱신한다.

사이트별 WP 비밀번호(REST 쓰기 권한) 필요 — GitHub Actions에서
secrets.<SITE> 환경변수로 주입해서 실행.
"""
import os
import re
import json
import requests

WP_USER = "huh0303@gmail.com"
MANIFEST_PATH = "ai_artifact_manifest.json"

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

# scan_ai_artifacts.py의 SAFE_TO_STRIP과 동일한 패턴(실제 제거 실행용)
STRIP_PATTERNS = [
    r'<p>\s*body\s*HTML\s*</p>\s*',
    r'(?<![a-zA-Z])body\s+HTML(?![a-zA-Z])',
    r'\[OUTPUT FORMAT[^\]]*\]',
    r"\[THIS SITE.?S UNIQUE STRUCTURE[^\]]*\]",
    r'<p>\s*FAQ_START\s*</p>\s*',
    r'<p>\s*FAQ_END\s*</p>\s*',
    r'^\s*FAQ_START\s*$',
    r'^\s*FAQ_END\s*$',
    r'<p>\s*TITLE:\s*</p>\s*',
    r'<p>\s*As an AI language model[^<]*</p>\s*',
    r"<p>\s*I'?m an AI[^<]*</p>\s*",
    r'<p>\s*I cannot browse the internet[^<]*</p>\s*',
    r'<p>\s*I do not have (real-time|access to real-time)[^<]*</p>\s*',
]


def log(msg):
    print(msg, flush=True)


def clean_content(content):
    removed = 0
    for pat in STRIP_PATTERNS:
        content, n = re.subn(pat, '', content, flags=re.IGNORECASE | re.MULTILINE)
        removed += n
    return content, removed


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    ok = fail = skip = 0
    for item in manifest:
        site = item["site"]
        post_id = item["post_id"]
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

        new_content, removed = clean_content(content)
        if removed == 0:
            log(f"[{site}#{post_id}] ⚠️ 패턴 매칭 실패 (이미 수정됨?) → 건너뜀")
            skip += 1
            continue

        try:
            pr = requests.post(
                f"{site}/wp-json/wp/v2/posts/{post_id}",
                auth=auth, json={"content": new_content}, timeout=30,
            )
        except Exception as e:
            log(f"[{site}#{post_id}] ⚠️ 업데이트 오류: {e}")
            fail += 1
            continue

        if pr.status_code in (200, 201):
            log(f"[{site}#{post_id}] ✅ AI 흔적 {removed}건 제거 완료")
            ok += 1
        else:
            log(f"[{site}#{post_id}] ⚠️ 업데이트 실패 HTTP {pr.status_code}: {pr.text[:150]}")
            fail += 1

    log("=" * 60)
    log(f"완료: 성공 {ok} / 실패 {fail} / 건너뜀 {skip} (대상 {len(manifest)}개 글)")


if __name__ == "__main__":
    main()
