#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regenerate_sis_pages.py

sis-korea.com 고정 페이지(홈/소개/학사/연락처)에 남아있는 이전 워드프레스 테마
("Champion School" 데모 콘텐츠, "Hello world!" 샘플 글 등) 찌꺼기를
실제 사이트 정체성(서울국제대학교 SIS - 유학 지원 정보 플랫폼)으로 교체한다.

regenerate_sis_placeholder.py 와의 차이:
  - 그 스크립트는 '글(post)'만 대상으로 함 (/wp/v2/posts)
  - 이 스크립트는 '고정 페이지(page)'를 대상으로 함 (/wp/v2/pages)
  - 정체성 페이지는 AI 생성 파이프라인을 타지 않고 고정된 실제 문구로 직접 교체함
    (홈/소개 페이지 같은 신뢰성이 중요한 페이지는 AI 생성보다 정확성이 우선이라는 판단)

실행 전 확인:
  - autopost_mega.py 의 SITES_CONFIG 에 sis-korea.com 항목이 있고
    wp_pass_env 로 지정된 시크릿이 GitHub Actions secrets 에 등록돼 있어야 함
  - PAGE_CONTENT 의 문구는 초안입니다. 실제 배포 전 검수 권장합니다.
"""
import os, sys, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import autopost_mega as ap  # noqa: E402  (기존 파이프라인의 SITES_CONFIG, WP_USER 재사용)

SITE_URL = "https://sis-korea.com"
SITE_NAME_KO = "서울국제대학교 SIS"
SITE_NAME_EN = "Seoul International University (SIS)"

# key -> 매칭할 slug 조각들 / 새 제목·본문
PAGE_CONTENT = {
    "home": {
        "match": ["home"],  # 프론트페이지는 별도 판별 로직으로도 잡음 (아래 참고)
        "title": SITE_NAME_KO,
        "content": f"""
<h1>{SITE_NAME_EN}</h1>
<p>{SITE_NAME_KO}는 한국 유학을 준비하는 외국인 학생들을 위해
학사 프로그램(Programs), 장학금(Scholarships), TOPIK 준비 정보를
제공하는 유학 지원 정보 플랫폼입니다.</p>
<p>카테고리별로 실질적인 정보를 정리해 제공하고 있습니다:
Programs · Scholarships · TOPIK</p>
""".strip(),
    },
    "about": {
        "match": ["about"],
        "title": "About / 소개",
        "content": f"""
<h1>About {SITE_NAME_EN}</h1>
<p>{SITE_NAME_KO}는 한국 유학을 준비하는 외국인 학생과 학부모에게
신뢰할 수 있는 정보를 전달하기 위해 운영되고 있습니다.</p>
<h2>제공 정보</h2>
<ul>
<li>Programs — 학과 및 프로그램 안내</li>
<li>Scholarships — 장학금 정보 및 지원 절차</li>
<li>TOPIK — 한국어능력시험 준비 자료</li>
</ul>
""".strip(),
    },
    "academics": {
        "match": ["academic"],
        "title": "Academics / 학사정보",
        "content": f"""
<h1>Academics</h1>
<p>{SITE_NAME_KO}에서 제공하는 학사 일정, 프로그램 구성,
입학 절차 관련 정보를 안내합니다.</p>
""".strip(),
    },
    "contact": {
        "match": ["contact"],
        "title": "Contact / 문의",
        "content": """
<h1>Contact</h1>
<p>문의사항은 사이트 내 문의 양식을 이용해주세요.</p>
""".strip(),
    },
}


def find_site_config(url):
    for s in ap.SITES_CONFIG:
        if s["url"] == url:
            return s
    return None


def get_all_pages(site_url, pw):
    pages = []
    page_num = 1
    while True:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/pages",
            auth=(ap.WP_USER, pw),
            params={"per_page": 50, "page": page_num, "context": "edit",
                    "_fields": "id,slug,title,link"},
            timeout=20,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        pages.extend(batch)
        page_num += 1
        if page_num > 5:  # 안전장치: 250개 이상은 없다고 가정
            break
    return pages


def get_front_page_id(site_url, pw):
    """워드프레스 설정에서 '홈페이지로 표시' 지정된 page_on_front id 조회 시도"""
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/settings",
                          auth=(ap.WP_USER, pw), timeout=15)
        if r.status_code == 200:
            return r.json().get("page_on_front") or None
    except Exception:
        pass
    return None


def update_page(site_url, pw, page_id, title, content):
    data = {"title": title, "content": content, "status": "publish"}
    r = requests.post(f"{site_url}/wp-json/wp/v2/pages/{page_id}",
                       auth=(ap.WP_USER, pw), json=data, timeout=30)
    if r.status_code in (200, 201):
        return {"ok": True, "id": page_id, "url": r.json().get("link", "")}
    return {"ok": False, "status": r.status_code, "error": r.text[:300]}


def main():
    site = find_site_config(SITE_URL)
    if not site:
        print("❌ 사이트 설정을 찾지 못함 (autopost_mega.py SITES_CONFIG 확인)")
        return
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        print(f"❌ 비밀번호 없음: {site['wp_pass_env']} (GitHub secrets 확인)")
        return

    pages = get_all_pages(SITE_URL, pw)
    print(f"고정 페이지 {len(pages)}개 로드")

    front_id = get_front_page_id(SITE_URL, pw)
    if front_id:
        print(f"프론트페이지 id={front_id} 확인됨")

    results = []
    matched_keys = set()

    for page in pages:
        slug = (page.get("slug") or "").lower()

        # 프론트페이지 우선 매칭
        if front_id and page["id"] == front_id and "home" not in matched_keys:
            spec = PAGE_CONTENT["home"]
            res = update_page(SITE_URL, pw, page["id"], spec["title"], spec["content"])
            res.update({"page_key": "home", "old_slug": slug})
            results.append(res)
            matched_keys.add("home")
            print(f"{'✅' if res['ok'] else '❌'} home (front, slug={slug}) -> "
                  f"{res.get('url', res.get('error'))}")
            continue

        for key, spec in PAGE_CONTENT.items():
            if key in matched_keys:
                continue
            if any(m in slug for m in spec["match"]):
                res = update_page(SITE_URL, pw, page["id"], spec["title"], spec["content"])
                res.update({"page_key": key, "old_slug": slug})
                results.append(res)
                matched_keys.add(key)
                print(f"{'✅' if res['ok'] else '❌'} {key} (slug={slug}) -> "
                      f"{res.get('url', res.get('error'))}")
                break

    missing = set(PAGE_CONTENT.keys()) - matched_keys
    if missing:
        print(f"⚠️ 매칭 안 된 페이지: {missing} — 실제 slug을 직접 확인해서 "
              f"PAGE_CONTENT의 'match' 목록에 추가해야 할 수 있습니다.")

    with open("regenerate_sis_pages_result.txt", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"{r}\n")
        if missing:
            f.write(f"missing={missing}\n")


if __name__ == "__main__":
    main()
