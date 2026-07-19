#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
27개 사이트 카테고리 건강도 개선 + 포커스키워드 백필
1) Etc류 중복 카테고리 병합 (예: Etc + ETC-Uncategorized -> Etc)
2) 진짜 빈 카테고리(count=0, Etc 자신은 제외) 삭제
3) Etc/기타에 쌓인 글을 본문+제목 기반으로 실제 카테고리로 재분류 (약할 때만 Gemini 보조)
4) rank_math_focus_keyword 없는 글에 제목에서 핵심어 추출해 백필
"""
import os, re, json, html as _html
import requests

WP_USER = "huh0303@gmail.com"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    ("https://kskin365.com", "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]

ETC_ALIAS_RE = re.compile(r'^(etc\.?|기타|etc-?uncategorized|other|others)$', re.IGNORECASE)

# 제목 템플릿(22종) 접두/접미 제거 -> 남는 부분을 포커스키워드로 사용
TEMPLATE_STRIP_PREFIX = re.compile(
    r'^(Before You Try|Is |Study Reveals:?\s*\d*\s*(in|of)?\s*\d*\s*People\s*(Misunderstand)?|'
    r'How to Actually Handle|A Practical Look at|The Real Cost of|The Truth About|Rethinking |'
    r'Behind the Scenes:\s*What |Why Does |\d+\s*(Things|Mistakes)\s*(About|People Make With)\s*|'
    r'What Nobody Tells You About|\d+\s*Mistakes People Make With)\s*',
    re.IGNORECASE)
TEMPLATE_STRIP_SUFFIX = re.compile(
    r'(:\s*A (Specialist.?s|Closer)\s*(Guide|Look).*|,\s*Read This First.*|'
    r'\s*Really Worth It\?.*|Explained in Plain English.*|:\s*What (Most People Get Wrong|to Expect|'
    r'First-Timers Should Know).*|Warning Signs.*|Has (Changed|Really Changed).*|'
    r'(Should\s*)?Know.*|Q&A:.*|101:.*|Frequently Overlooked Facts.*|Complete Guide.*|'
    r'Dreams?\s*A Closer Look.*|Foreigners? Top \d+.*)$',
    re.IGNORECASE)


def auth(pw):
    return requests.auth.HTTPBasicAuth(WP_USER, pw)


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


def get_categories(url, pw):
    cats = []
    page = 1
    while True:
        r = requests.get(f"{url}/wp-json/wp/v2/categories", auth=auth(pw),
                          params={"per_page": 100, "page": page}, timeout=15)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        cats.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return cats


def get_posts_in_category(url, pw, cat_id):
    posts = []
    page = 1
    while True:
        r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=auth(pw),
                          params={"categories": cat_id, "per_page": 100, "page": page,
                                  "status": "publish", "_fields": "id,title,content"}, timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def move_post_category(url, pw, post_id, new_cat_id):
    r = requests.post(f"{url}/wp-json/wp/v2/posts/{post_id}", auth=auth(pw),
                       json={"categories": [new_cat_id]}, timeout=15)
    return r.status_code in (200, 201)


def delete_category(url, pw, cat_id):
    r = requests.delete(f"{url}/wp-json/wp/v2/categories/{cat_id}", auth=auth(pw),
                         params={"force": True}, timeout=15)
    return r.status_code in (200, 201)


def gemini_pick_category(title, content_snippet, candidates):
    if not GEMINI_API_KEY or not candidates:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        cand_str = ", ".join(candidates)
        prompt = (f"다음 글을 아래 카테고리 중 하나로 분류해줘. 카테고리 이름만 정확히 그대로 답해.\n"
                  f"카테고리 목록: {cand_str}\n"
                  f"제목: {title}\n본문 일부: {content_snippet[:400]}\n답(카테고리 이름만):")
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 20})
        picked = (resp.text or "").strip().strip('."\'')
        for c in candidates:
            if c.strip().lower() == picked.lower():
                return c
    except Exception as e:
        print(f"      ⚠️ Gemini 분류 실패: {e}")
    return None


def match_category(title, content_plain, candidates):
    """제목+본문 기반 스코어 매칭. candidates: [(id,name), ...] (Etc 제외)"""
    text = f"{title} {content_plain[:1500]}".lower()
    text_nospace = re.sub(r'[\s/,\-]+', '', text)
    words = [w for w in re.split(r'[\s/,\-]+', text) if len(w) > 2]

    best, best_score = None, 0
    for cid, name in candidates:
        cat_words = [w for w in re.split(r'[\s/,\-]+', name.lower()) if len(w) > 2]
        score = 0
        for cw in cat_words:
            stem = cw[:5] if len(cw) > 5 else cw
            for w in words:
                if w.startswith(stem) or stem.startswith(w[:5]):
                    score += 1
                    break
        name_nospace = re.sub(r'[\s/,\-]+', '', name.lower())
        if len(name_nospace) >= 2:
            for i in range(len(name_nospace) - 1):
                if name_nospace[i:i+2] in text_nospace:
                    score += 0.5
        if name.strip().lower() in text:
            score += 5
        if score > best_score:
            best, best_score = (cid, name), score
    return best, best_score


def derive_focus_keyword(title):
    t = _html.unescape(strip_tags(title))
    t2 = TEMPLATE_STRIP_PREFIX.sub('', t)
    t2 = TEMPLATE_STRIP_SUFFIX.sub('', t2)
    t2 = t2.strip(" :,-")
    if len(t2) < 3:
        t2 = t
    return t2[:60]


def process_site(url, pw, log):
    log(f"\n🌐 {url}")
    cats = get_categories(url, pw)
    cats = [c for c in cats if c.get("name", "").strip().lower() not in ("uncategorized", "미분류")]

    # ── 1) Etc류 별칭 그룹핑 ──
    etc_group = [c for c in cats if ETC_ALIAS_RE.match(c.get("name", "").strip())]
    canonical = None
    if etc_group:
        canonical = max(etc_group, key=lambda c: (c["name"].strip().lower() in ("etc", "기타"), c.get("count", 0)))
        for c in etc_group:
            if c["id"] == canonical["id"]:
                continue
            if c.get("count", 0) > 0:
                posts = get_posts_in_category(url, pw, c["id"])
                for p in posts:
                    move_post_category(url, pw, p["id"], canonical["id"])
                log(f"  🔀 '{c['name']}'({c.get('count',0)}건) → '{canonical['name']}' 병합")
            ok = delete_category(url, pw, c["id"])
            log(f"  🗑️ 중복 카테고리 삭제: {c['name']} ({'성공' if ok else '실패'})")

    # ── 2) 진짜 빈 카테고리 삭제 (Etc 자신 제외) ──
    cats2 = get_categories(url, pw)
    cats2 = [c for c in cats2 if c.get("name", "").strip().lower() not in ("uncategorized", "미분류")]
    canon_id = canonical["id"] if canonical else None
    for c in cats2:
        if c["id"] == canon_id:
            continue
        if c.get("count", 0) == 0:
            ok = delete_category(url, pw, c["id"])
            log(f"  🗑️ 빈 카테고리 삭제: {c['name']} ({'성공' if ok else '실패'})")

    # ── 3) Etc 재분류 ──
    cats3 = get_categories(url, pw)
    cats3 = [c for c in cats3 if c.get("name", "").strip().lower() not in ("uncategorized", "미분류")]
    etc_final = None
    for c in cats3:
        if ETC_ALIAS_RE.match(c.get("name", "").strip()):
            etc_final = c
            break
    real_candidates = [(c["id"], c["name"]) for c in cats3 if not (etc_final and c["id"] == etc_final["id"])]

    moved = 0
    if etc_final and etc_final.get("count", 0) > 0 and real_candidates:
        posts = get_posts_in_category(url, pw, etc_final["id"])
        cand_names = [n for _, n in real_candidates]
        for p in posts:
            title = _html.unescape(strip_tags(p.get("title", {}).get("rendered", "")))
            content_plain = strip_tags(p.get("content", {}).get("rendered", ""))
            best, score = match_category(title, content_plain, real_candidates)
            if not best or score < 3:
                picked_name = gemini_pick_category(title, content_plain, cand_names)
                if picked_name:
                    for cid, n in real_candidates:
                        if n == picked_name:
                            best = (cid, n)
                            break
            if best:
                if move_post_category(url, pw, p["id"], best[0]):
                    moved += 1
        log(f"  📦 Etc({etc_final.get('count',0)}건) 중 {moved}건 재분류 완료")

    # ── 4) 포커스키워드 백필 ──
    filled = 0
    page = 1
    while True:
        r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=auth(pw),
                          params={"per_page": 100, "page": page, "status": "publish",
                                  "_fields": "id,title,meta"}, timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            meta = p.get("meta", {}) or {}
            kw = meta.get("rank_math_focus_keyword", "")
            if kw and str(kw).strip():
                continue
            new_kw = derive_focus_keyword(p.get("title", {}).get("rendered", ""))
            if not new_kw:
                continue
            rr = requests.post(f"{url}/wp-json/wp/v2/posts/{p['id']}", auth=auth(pw),
                                json={"meta": {"rank_math_focus_keyword": new_kw}}, timeout=15)
            if rr.status_code in (200, 201):
                filled += 1
        if len(batch) < 100:
            break
        page += 1
    log(f"  🔑 포커스키워드 백필: {filled}건")


def main():
    lines = []

    def log(m):
        print(m)
        lines.append(m)

    for url, env_key in SITES:
        pw = os.getenv(env_key, "")
        if not pw:
            log(f"\n🌐 {url}\n  ⚠️ 비밀번호 없음 — 스킵")
            continue
        try:
            process_site(url, pw, log)
        except Exception as e:
            log(f"  ❌ 사이트 처리 오류: {e}")

    with open("fix_categories_and_keywords_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
