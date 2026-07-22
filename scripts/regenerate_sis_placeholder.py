#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regenerate_sis_placeholder.py
sis-korea.com의 "Why Does 추가 Cause Problems? Experts Explain" 글은
load_keyword() 버그로 플레이스홀더 '추가'가 키워드로 뽑혀서 발행된, 주제 자체가
의미없는 글이다. 단순 텍스트 치환으로는 못 고치므로 실제 파이프라인(Gemini 생성 ->
SEO 재생성 루프 -> 이미지 -> 발행 요소 조립)을 그대로 재사용해서 정상 주제
(Scholarships)로 콘텐츠를 완전히 새로 만들고, 기존 글(같은 post id)을 업데이트한다.
"""
import os, sys, re, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import autopost_mega as ap

TARGET_SLUG_HINT = "why-does"
TARGET_TITLE_HINT = "추가"
NEW_KEYWORD = "Scholarships"

def find_site_config(url):
    for s in ap.SITES_CONFIG:
        if s["url"] == url:
            return s
    return None

def find_target_post(site_url, pw):
    r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(ap.WP_USER, pw),
                      params={"per_page": 50, "search": TARGET_TITLE_HINT,
                              "context": "edit", "_fields": "id,title,link,slug"},
                      timeout=20)
    if r.status_code != 200:
        print(f"❌ 글 검색 실패: {r.status_code} {r.text[:200]}")
        return None
    for p in r.json():
        t = re.sub(r'<[^>]+>', '', p["title"].get("raw") or p["title"]["rendered"])
        if TARGET_TITLE_HINT in t or TARGET_SLUG_HINT in p.get("slug", ""):
            return p
    return None

def wp_update_post(site, existing_id, title, body_html, meta, tags, faq, images, keyword, score, reporter):
    """wp_post()와 동일한 조립 로직이지만, 새 글을 만들지 않고 기존 post_id를 업데이트한다."""
    pw = os.getenv(site["wp_pass_env"], "")
    url = site["url"]; theme = site["theme"]

    author_id = ap.get_or_create_wp_author(url, pw, reporter)
    cat_id = ap.pick_best_category(url, pw, keyword, title)
    cat_name = ap.get_category_for_post(theme, keyword, title)

    hero = ap.build_img_html(images[:1], keyword)
    mid  = ap.build_img_html(images[1:2], keyword) if len(images) > 1 else ""
    end  = ap.build_img_html(images[2:3], keyword) if len(images) > 2 else ""
    faq_html = ap.build_faq_html(faq)

    h2ends = [m.end() for m in re.finditer(r'</h2>', body_html, re.IGNORECASE)]
    ins = -1
    if len(h2ends) >= 2:
        pm = re.search(r'</p>', body_html[h2ends[1]:], re.IGNORECASE)
        if pm: ins = h2ends[1] + pm.end()
    if ins < 0:
        half = len(body_html) // 2
        pm = re.search(r'</p>', body_html[half:], re.IGNORECASE)
        ins = half + pm.end() if pm else half

    final = hero + body_html[:ins] + (mid if mid else "") + body_html[ins:] + end + faq_html
    final += ap.build_cta_html(url, site.get("lang", "ko"))
    final += ap.build_author_bio_html(url, site.get("lang", "ko"), reporter, keyword)
    final += ap.build_related_links_html(url, pw, site.get("lang", "ko"), exclude_title=title)

    tag_ids = []
    for tag in tags:
        try:
            tr = requests.post(f"{url}/wp-json/wp/v2/tags", auth=(ap.WP_USER, pw), json={"name": tag}, timeout=10)
            if tr.status_code in (200, 201):
                tag_ids.append(tr.json().get("id"))
            elif tr.status_code == 400:
                sr = requests.get(f"{url}/wp-json/wp/v2/tags", auth=(ap.WP_USER, pw),
                                   params={"search": tag, "per_page": 1}, timeout=10)
                if sr.status_code == 200 and sr.json():
                    tag_ids.append(sr.json()[0]["id"])
        except Exception:
            pass

    rank_kw = ",".join([keyword] + tags[:4])
    new_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]

    data = {
        "title": title, "content": final, "status": "publish", "slug": new_slug,
        "categories": [cat_id] if cat_id and cat_id > 0 else [],
        "tags": tag_ids,
        "meta": {"rank_math_focus_keyword": rank_kw, "rank_math_description": meta,
                 "rank_math_seo_score": str(score)},
    }
    if author_id and author_id > 0:
        data["author"] = author_id

    r = requests.post(f"{url}/wp-json/wp/v2/posts/{existing_id}", auth=(ap.WP_USER, pw), json=data, timeout=30)
    if r.status_code in (200, 201):
        purl = r.json().get("link", "")
        ap.ping_indexnow(purl, url)
        return {"ok": True, "post_id": existing_id, "url": purl, "author": reporter["name"], "category": cat_name}
    return {"ok": False, "status": r.status_code, "error": r.text[:400]}

def main():
    site_url = "https://sis-korea.com"
    site = find_site_config(site_url)
    if not site:
        print("❌ 사이트 설정을 찾지 못함"); return

    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        print(f"❌ 비밀번호 없음: {site['wp_pass_env']}"); return

    target = find_target_post(site_url, pw)
    if not target:
        print("❌ 대상 글을 찾지 못함 (이미 수정됐거나 삭제됐을 수 있음)"); return

    print(f"대상 글: {target['title']['rendered']}")
    print(f"URL: {target['link']} (id={target['id']})")

    keyword = ap.sanitize_keyword(NEW_KEYWORD, f"{site['theme']} guide 2026")
    reporter = ap.pick_reporter(site)
    p = ap.SITE_PERSONA.get(site_url, {})
    min_chars = p.get("min_chars", 2200)

    base_prompt = ap.make_site_prompt(keyword, site, reporter)
    prompt = base_prompt
    best_score = 0
    best_result = None

    for attempt in range(ap.MAX_REGEN + 1):
        raw = ap.generate_content_gemini(prompt)
        body_raw, title, meta, faq = ap.extract_meta_and_faq(raw)
        body, tags = ap.extract_tags(body_raw, keyword, site["theme"], site["lang"])
        title = ap.build_diverse_title(keyword, site["lang"], site_url=site_url)

        score = ap.estimate_seo_score(title, body, meta, tags, faq, ["x", "x", "x"], keyword)
        print(f"  {attempt+1}회차 -> SEO {score}점")
        if score > best_score:
            best_score = score
            best_result = (body, title, meta, faq, tags)
        if score >= ap.SEO_TARGET:
            break
        if attempt < ap.MAX_REGEN:
            issues = []
            plain = re.sub(r'<[^>]+>', '', body)
            blen = len(plain.replace(' ', '').replace('\n', ''))
            if blen < min_chars: issues.append(f"본문 {blen}자->{min_chars}자 증량")
            suffix = f"\n\n[SEO {score}점 미달 보완]\n" + "".join(f"{i+1}. {x}\n" for i, x in enumerate(issues))
            suffix += "\n위 항목 모두 충족하여 처음부터 다시 작성."
            prompt = base_prompt + suffix

    body, title, meta, faq, tags = best_result

    # ★ 안전장치 재적용 (혹시 모를 잔재 제거)
    title = ap.strip_hash_artifacts(title)
    body = ap.strip_hash_artifacts(body)
    meta = ap.strip_hash_artifacts(meta)
    faq = [(ap.strip_hash_artifacts(q), ap.strip_hash_artifacts(a)) for q, a in faq] if faq else faq
    tags = [ap.strip_hash_artifacts(t) for t in tags] if tags else tags

    images = ap.get_multiple_images(keyword, count=3, theme=site["theme"])
    print(f"이미지 {len(images)}장, 최종 SEO {best_score}점")

    result = wp_update_post(site, target["id"], title, body, meta, tags, faq, images, keyword, best_score, reporter)
    if result["ok"]:
        print(f"✅ 재발행 완료: {result['url']}")
    else:
        print(f"❌ 실패: {result}")

    with open("regenerate_sis_placeholder_result.txt", "w", encoding="utf-8") as f:
        f.write(f"target_old_url={target['link']}\n")
        f.write(f"result={result}\n")

if __name__ == "__main__":
    main()
