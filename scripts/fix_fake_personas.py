#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fake_personas.py

k-health365.com 기존 발행글에서 "OOO 교수", "OOO 원장", "OO병원 OO과 전문의" 같이
실존 확인이 안 되는 특정 개인+병원 인용 패턴을 탐지하고,
Gemini를 통해 "그 부분만" 기관명 인용으로 안전하게 재작성합니다.
(전체 재작성이 아니라 해당 문장만 최소 수정 — 나머지 본문은 그대로 유지하도록 강하게 지시)

안전장치:
- 재작성 후 길이가 원문 대비 ±20% 벗어나면 "이상치"로 보고 자동 반영하지 않고 로그만 남김
- 실제 반영 여부는 APPLY_FIX 플래그로 제어 (기본 True — 사용자가 즉시 반영 요청함)
"""
import os, re, requests, json, time

APPLY_FIX = True   # False로 하면 탐지/재작성 결과만 로그로 남기고 실제 반영은 안 함

SITE_URL = "https://k-health365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS_ENV = "KHEALTH365COM"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

NAME_PROF_PATTERN = re.compile(r'[가-힣]{2,4}\s*(교수|원장)')
HOSPITAL_EXPERT_PATTERN = re.compile(r'[가-힣]{2,12}(대학교병원|대학병원|병원)\s*[가-힣]{0,8}\s*전문의')

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))


def fetch_all_posts(pw):
    posts = []
    page = 1
    while True:
        r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts",
                          auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                          params={"per_page": 50, "page": page, "status": "publish",
                                  "_fields": "id,title,link,content"},
                          timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return posts


def find_matches(html):
    matches = set(m.group(0) for m in NAME_PROF_PATTERN.finditer(html))
    matches |= set(m.group(0) for m in HOSPITAL_EXPERT_PATTERN.finditer(html))
    return matches


def gemini_rewrite(html, matches):
    import urllib.request
    prompt = f"""아래는 건강정보 블로그 글의 HTML 본문입니다.
이 본문 안에 실존 확인이 되지 않는 특정 개인(가상의 교수/원장/전문의 이름)이
특정 병원 소속으로 인용된 부분이 있습니다. 다음 패턴들이 발견되었습니다:
{', '.join(matches)}

**지시사항 (매우 중요):**
1. 위 패턴이 포함된 문장만 찾아서, 특정 개인 이름과 소속 병원을 지어내는 대신
   "대한의학회에 따르면", "질병관리청 가이드라인에 의하면", "국내 대학병원 임상 자료에 따르면" 등
   기관명 기반 인용으로 바꾸세요.
2. 그 외 나머지 본문은 단 한 글자도 바꾸지 마세요. HTML 구조, 다른 문장, 문단 순서 전부 원본 그대로 유지.
3. 출력은 전체 수정된 HTML 본문만 출력하세요. 설명, 주석, 마크다운 코드블록 표시 없이 순수 HTML만.

원본 본문:
{html}
"""
    body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log(f"   ⚠️ Gemini 오류: {e}")
        return None


def main():
    pw = os.environ.get(WP_PASS_ENV)
    if not pw or not GEMINI_API_KEY:
        log("⚠️ 환경변수(KHEALTH365COM 또는 GEMINI_API_KEY) 없음")
        return

    posts = fetch_all_posts(pw)
    log(f"전체 게시물 {len(posts)}개 스캔 중...")

    flagged = []
    for p in posts:
        html = p.get("content", {}).get("rendered", "")
        matches = find_matches(html)
        if matches:
            flagged.append((p, matches))

    log(f"가짜 인물/병원 인용 패턴 발견: {len(flagged)}개 게시물\n")

    fixed, skipped, failed = 0, 0, 0
    for p, matches in flagged:
        title = p.get("title", {}).get("rendered", "")
        log(f"#{p['id']} {title[:40]} | 패턴: {', '.join(list(matches)[:3])}")

        html = p.get("content", {}).get("rendered", "")
        new_html = gemini_rewrite(html, matches)
        time.sleep(2)  # RPM 보호

        if not new_html:
            failed += 1
            continue

        old_len, new_len = len(html), len(new_html)
        ratio = new_len / old_len if old_len else 0
        if ratio < 0.8 or ratio > 1.2:
            log(f"   ⚠️ 길이 변화 이상치({old_len}->{new_len}, {ratio:.0%}) → 자동반영 스킵, 수동확인 필요")
            skipped += 1
            continue

        # 재작성 후에도 패턴이 남아있는지 재확인
        remaining = find_matches(new_html)
        if remaining:
            log(f"   ⚠️ 재작성 후에도 패턴 잔존: {remaining} → 스킵")
            skipped += 1
            continue

        if APPLY_FIX:
            up = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{p['id']}",
                                auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                json={"content": new_html}, timeout=30)
            if up.status_code in (200, 201):
                fixed += 1
                log(f"   ✅ 수정 반영 완료")
            else:
                failed += 1
                log(f"   ⚠️ 반영 실패 status={up.status_code}")
        else:
            fixed += 1
            log(f"   (미리보기 모드 — 실제 반영 안 함)")

    log(f"\n요약: 탐지 {len(flagged)} / 반영 {fixed} / 스킵(수동확인필요) {skipped} / 실패 {failed}")
    with open("fix_fake_personas_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))


if __name__ == "__main__":
    main()
