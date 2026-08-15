#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_ai_toned_posts.py
─────────────────────────────────────────────────────────────
27개 사이트 전체 발행글을 훑어서 "대수술"한다.

사용자 지시 히스토리(2026-08-14, 점점 더 공격적으로 명확해짐):
  1. "AI 티 나는 것은 비공개나 삭제로. 글 수 적은게 낫다."
  2. "색인이 된거 빼고 대부분 지울래" / "조금이라도 의심되면 싹 지우자"
  3. 최종: "대수술 해줘. 구글 색인 되어 있는것만 남기던지."
→ 최종 판단 기준은 AI 티 패턴 매칭이 아니라 **"구글에 실제 색인됐는가"** 하나로
단순화했다: 색인된 글만 남기고, 나머지는 전부(AI 티가 있든 없든) 비공개 전환.
색인 안 된 글은 어차피 검색 유입에 기여를 못 하고 있으니 품질과 무관하게 정리
대상 — daily_site_traffic.py와 동일한 Search Console URL 검사 API로 낱개 URL의
실제 색인 여부를 확인한다. AI 티 패턴 매칭은 게이트가 아니라 리포트에 참고
정보로만 같이 남긴다.

2026-08-15 정정: 이전 버전은 "확인 자체가 실패하면(할당량 초과/네트워크 오류
등) 안전하게 색인 안 됨으로 간주"했으나, 이게 오히려 위험한 것으로 드러남 —
Search Console URL 검사 API는 분당/일일 호출 한도가 낮아서 27개 사이트를
한 번에 훑으면 중간에 429(할당량 초과)가 나기 시작하고, 그 뒤로는 모든 글이
"확인 실패"가 되어 전부 "미색인"으로 뭉개진다(k-health365.com이 실제로는
색인된 글이 있는데도 0/243으로 오탐된 사고의 원인). 그래서 지금은 API
호출 실패(None)와 "API는 성공했지만 Google이 색인 안 됨이라 응답"(False)을
명확히 분리한다 — 실패는 uncertain 버킷으로 따로 모으고, --execute에서도
**절대 자동으로 비공개 전환하지 않는다**(색인 확인이 안 됐다는 이유로 멀쩡한
글을 지우는 사고를 막기 위함). 또한 429가 연속으로 감지되면 이후 나머지는
호출 자체를 건너뛰고 전부 uncertain으로 표시한다(의미 없는 API 호출 낭비 방지).

삭제보다 안전한 '비공개(private) 전환'을 기본 동작으로 한다 — 복구 가능,
검색엔진에서도 즉시 빠짐.

기본값은 DRY RUN(리포트만, 실제 변경 없음) — 안전을 위해 명시적으로
--execute 를 줘야 실제로 비공개 전환한다. 사이트별 WP 비밀번호는
autopost_mega.py의 SITE_SECRET_MAP과 동일한 이름의 환경변수로 주입.
색인 확인용 GSC_SERVICE_ACCOUNT_JSON이 반드시 필요 — 없으면 색인 여부를
전혀 판단할 수 없으므로 안전하게 전체 스킵하고 에러로 종료한다(예전처럼
"게이트 없이 전체 정리 대상"으로 밀어붙이면, 색인 확인이 안 됐다는 이유로
멀쩡한 색인글까지 지울 위험이 있어 이번 "색인만 기준" 모드에서는 허용하지 않음).
"""
import os
import re
import sys
import json
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from daily_site_traffic import get_gsc_token, gsc_get, inspect_url_index_status
    GSC_AVAILABLE = True
except Exception:
    GSC_AVAILABLE = False

WP_USER = "huh0303@gmail.com"

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

MANIFEST_PATH = "ai_toned_posts_manifest.json"

# make_site_prompt에서 금지시킨 것과 동일한 패턴군 — 과거 글에 남아있는지 탐지용
AI_TELL_PATTERNS = [
    # 한글 — 수사의문문 연쇄/충격유도
    r'하시나요\?', r'해보셨나요\?', r'되셨나요\?', r'있으신가요\?',
    r'몰랐죠\?', r'알고 계셨나요\?', r'궁금하지 않으세요\?',
    r'충격적인 사실', r'\d+%[^가-힣]{0,3}나 된다는 사실',
    r'오늘은?\s*.{0,20}함께\s*알아보', r'오늘,?\s*.{0,20}알아보아요',
    r'우리\s*몸은\s*정말\s*신비롭',
    r'이 글을 통해\s*.{0,20}(궁금증|해소)',
    r'현대\s*사회에서', r'현대인들에게', r'중요성이?\s*점점\s*커지고\s*있',
    # 영어 — 동일 계열
    r'\bhave you ever wondered\b', r'\bdid you know\b',
    r'\bwhat if I told you\b', r'a staggering \d+%', r'surprisingly, \d+%',
    r"in this article, we'?ll explore", r"today, let'?s dive into",
    r'navigating the complexities', r"in today'?s fast-paced world",
    r'by the end of this article',
]
AI_TELL_RE = re.compile('|'.join(AI_TELL_PATTERNS), re.IGNORECASE)

# h2/h3 소제목이 물음표로 끝나는 것도 강한 신호
HEADING_QUESTION_RE = re.compile(r'<h[23][^>]*>[^<]*\?\s*</h[23]>', re.IGNORECASE)

# 2026-08-14 사용자 지시: "조금이라도 AI 티나면 싹 버리자, 절반 이상 없어져도 좋다"
# → 서로 다른 패턴 1개만 걸려도 정리 대상 (기존 2 → 1, 훨씬 공격적)
FLAG_THRESHOLD = 1


def log(msg):
    print(msg, flush=True)


def score_ai_tell(title, content):
    text = f"{title} {content}"
    hits = set(m.group(0).lower() for m in AI_TELL_RE.finditer(text))
    heading_hits = len(HEADING_QUESTION_RE.findall(content))
    total_signals = len(hits) + (1 if heading_hits else 0)
    return total_signals, sorted(hits)[:5], heading_hits


def fetch_all_posts(site_url, wp_pass):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/posts",
                params={"per_page": 50, "page": page, "status": "publish", "_fields": "id,title,content,link"},
                auth=(WP_USER, wp_pass), timeout=30,
            )
        except Exception as e:
            log(f"  ⚠️ 요청 실패(page {page}): {e}")
            break
        if r.status_code != 200:
            if page == 1:
                log(f"  ⚠️ HTTP {r.status_code}: {r.text[:150]}")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1
    return posts


def set_private(site_url, wp_pass, post_id):
    r = requests.post(
        f"{site_url}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, wp_pass), json={"status": "private"}, timeout=20,
    )
    return r.status_code in (200, 201)


def resolve_query_site(domain, accessible):
    domain_property = f"sc-domain:{domain}"
    site_url = f"https://{domain}"
    if site_url in accessible:
        return site_url
    if domain_property in accessible:
        return domain_property
    return None


def main():
    execute = "--execute" in sys.argv
    only_site = None
    exclude_sites = set()
    for a in sys.argv[1:]:
        if a.startswith("--site="):
            only_site = a.split("=", 1)[1]
        elif a.startswith("--exclude="):
            exclude_sites = {s.strip() for s in a.split("=", 1)[1].split(",") if s.strip()}

    mode = "실행(비공개 전환)" if execute else "리포트만(DRY RUN)"
    log(f"{'='*60}")
    log(f"🔍 대수술 — 색인 안 된 글 전부 정리 대상 — {mode}")
    log(f"{'='*60}\n")

    if not (GSC_AVAILABLE and os.getenv("GSC_SERVICE_ACCOUNT_JSON")):
        log("❌ GSC_SERVICE_ACCOUNT_JSON 없음 — 색인 여부를 확인할 방법이 없어서 중단.")
        log("   (색인 확인 없이 돌리면 멀쩡한 색인글까지 잘못 지울 위험이 있어 허용 안 함)")
        raise SystemExit(1)

    gsc_token = get_gsc_token()
    r = gsc_get(gsc_token, "/sites")
    gsc_accessible = set()
    if r.status_code == 200:
        gsc_accessible = {s.get("siteUrl") for s in r.json().get("siteEntry", [])}
    log(f"✅ GSC 색인 확인 활성화 — 접근 가능 사이트 {len(gsc_accessible)}개\n")

    manifest = {}
    total_flagged = 0
    total_kept_indexed = 0
    total_uncertain = 0
    total_checked = 0
    quota_exhausted = False
    consecutive_quota_errors = 0
    QUOTA_ABORT_THRESHOLD = 5

    for site_url, secret_name in SITE_SECRET_MAP.items():
        if only_site and only_site not in site_url:
            continue
        if site_url in exclude_sites:
            log(f"⏭  {site_url} — 제외 대상, 스킵")
            continue
        wp_pass = os.getenv(secret_name, "")
        if not wp_pass:
            log(f"⏭  {site_url} — 비밀번호 없음(secret {secret_name}), 스킵")
            continue

        log(f"🌐 {site_url}")
        posts = fetch_all_posts(site_url, wp_pass)
        log(f"   {len(posts)}개 글 조사 중...")

        domain = site_url.rstrip("/").replace("https://", "")
        query_site = resolve_query_site(domain, gsc_accessible)
        if not query_site:
            log(f"   ⚠️ GSC 접근 권한 없음 — 색인 확인 불가, 이 사이트는 스킵(안전을 위해 아무것도 안 지움)\n")
            continue

        flagged = []
        kept_indexed = []
        uncertain = []
        for p in posts:
            title = p.get("title", {}).get("rendered", "")
            content = p.get("content", {}).get("rendered", "")
            link = p.get("link", "")
            score, hits, heading_hits = score_ai_tell(title, content)
            total_checked += 1

            if quota_exhausted:
                result = {"indexed": None, "verdict": None, "coverageState": None,
                          "error": "할당량 소진 이후 미확인"}
            elif link:
                result = inspect_url_index_status(gsc_token, query_site, link)
                if result["error"] and "429" in result["error"]:
                    consecutive_quota_errors += 1
                    if consecutive_quota_errors >= QUOTA_ABORT_THRESHOLD:
                        quota_exhausted = True
                        log("   🛑 GSC 429(할당량 초과) 연속 감지 — 이후 전부 '확인실패'로 표시하고 API 호출 중단")
                else:
                    consecutive_quota_errors = 0
            else:
                result = {"indexed": None, "verdict": None, "coverageState": None, "error": "링크없음"}

            entry = {
                "id": p["id"], "title": title, "link": link,
                "ai_tell_score": score, "matched": hits, "question_headings": heading_hits,
                "verdict": result.get("verdict"), "coverageState": result.get("coverageState"),
            }
            if result["indexed"] is True:
                kept_indexed.append(entry)
            elif result["indexed"] is False:
                flagged.append(entry)
            else:
                entry["check_error"] = result.get("error")
                uncertain.append(entry)
            if not quota_exhausted:
                time.sleep(0.4)

        total_flagged += len(flagged)
        total_kept_indexed += len(kept_indexed)
        total_uncertain += len(uncertain)
        manifest[site_url] = {"to_hide": flagged, "kept_indexed": kept_indexed, "uncertain": uncertain}
        log(f"   → 색인 확인 {len(posts)}건: 색인됨(유지) {len(kept_indexed)}건 / "
            f"미색인(정리 대상) {len(flagged)}건 / 확인실패(uncertain, 손대지 않음) {len(uncertain)}건")
        for f in flagged[:5]:
            tell = f" [AI티 {f['ai_tell_score']}점: {f['matched']}]" if f['ai_tell_score'] else ""
            log(f"      {f['title'][:50]}{tell}")
        if len(flagged) > 5:
            log(f"      ... 외 {len(flagged)-5}건")

        if execute:
            for f in flagged:
                ok = set_private(site_url, wp_pass, f["id"])
                log(f"      {'✅' if ok else '❌'} 비공개 전환: {f['title'][:40]}")
                time.sleep(0.3)
        log("")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=2)

    log(f"{'='*60}")
    log(f"✅ 완료 — 조사 {total_checked}건 / 색인됨(유지) {total_kept_indexed}건 / "
        f"미색인(정리 대상) {total_flagged}건 / 확인실패(uncertain) {total_uncertain}건")
    if quota_exhausted:
        log("   ⚠️ 이번 실행은 GSC 할당량 초과로 중간에 확인이 중단됐다 — uncertain 건수는 재조사 필요, 절대 정리 대상 아님")
    log(f"   {'실제 비공개 전환 완료(uncertain은 건드리지 않음)' if execute else '리포트만 저장됨 (ai_toned_posts_manifest.json) — 실행하려면 --execute 추가'}")
    log(f"{'='*60}")


if __name__ == "__main__":
    main()
