#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ginseng_post.py
k-health365.com "홍삼 효능과 부작용" 글 개별 수정:
  1) 본문 상단 ```html 코드펜스 찌꺼기 제거
  2) 본문 주제(홍삼)와 무관한 이미지를 홍삼 관련 이미지로 교체 (featured + 본문 첫 <img>)
"""
import os, re, requests

SITE_URL = "https://k-health365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["KHEALTH365COM"]
PIXABAY_KEY = os.environ.get("PIXABAY_KEY")
PEXELS_KEY = os.environ.get("PEXELS_KEY")

TARGET_URL_SLUG_HINT = "홍삼"

auth = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

def strip_code_fences(text):
    t = text.strip()
    t = re.sub(r'^```[a-zA-Z]*\s*\n?', '', t)
    t = re.sub(r'\n?```\s*$', '', t)
    t = "\n".join(l for l in t.split("\n") if l.strip() not in ("```", "```html", "```HTML"))
    # 스마트따옴표/HTML엔티티 변형(예: "`html, &#8220;`html, "'html 등) 및
    # <p>로 감싸진 잔여 펜스 단독 문단 제거
    quote_alt = r'(?:[\u201c\u2018"\']|&#8220;|&#8216;|&quot;|&ldquo;|&lsquo;)'
    t = re.sub(
        rf'<p>\s*{quote_alt}*\s*`{{1,3}}\s*(html)?\s*</p>\s*',
        '', t, flags=re.IGNORECASE)
    t = re.sub(rf'^{quote_alt}*\s*`{{1,3}}\s*(html)?\s*$', '', t, flags=re.IGNORECASE | re.MULTILINE)
    return t.strip()

def fetch_all_posts():
    posts = []
    page = 1
    while True:
        r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts", auth=auth,
                          params={"per_page": 50, "page": page, "status": "publish",
                                  "context": "edit",
                                  "_fields": "id,title,link,slug,content"}, timeout=20)
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

def get_images_pixabay(query, need=3):
    if not PIXABAY_KEY:
        return []
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}"
            f"&image_type=photo&per_page=20&safesearch=true&min_width=600", timeout=10)
        hits = r.json().get("hits", [])
        return [h["webformatURL"] for h in hits[:need] if h.get("webformatURL")]
    except Exception as e:
        log(f"  pixabay err: {e}")
        return []

def get_images_pexels(query, need=3):
    if not PEXELS_KEY:
        return []
    try:
        r = requests.get(f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=20",
                          headers={"Authorization": PEXELS_KEY}, timeout=10).json()
        photos = r.get("photos", [])
        return [(p.get("src", {}).get("large") or p.get("src", {}).get("medium", ""))
                for p in photos[:need] if p.get("src")]
    except Exception as e:
        log(f"  pexels err: {e}")
        return []

def upload_image_to_wp(url, filename):
    try:
        img = requests.get(url, timeout=20).content
        r = requests.post(f"{SITE_URL}/wp-json/wp/v2/media", auth=auth,
                           headers={"Content-Disposition": f'attachment; filename="{filename}.jpg"',
                                    "Content-Type": "image/jpeg"}, data=img, timeout=30)
        if r.status_code in (200, 201):
            return r.json()
        log(f"  media upload fail {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log(f"  media upload err: {e}")
    return None

def main():
    posts = fetch_all_posts()
    log(f"전체 발행글 {len(posts)}건 로드")

    target = None
    for p in posts:
        title_plain = re.sub(r'<[^>]+>', '', p["title"]["rendered"])
        if TARGET_URL_SLUG_HINT in p.get("slug", "") or TARGET_URL_SLUG_HINT in title_plain:
            target = p
            break

    if not target:
        log("❌ 대상 글(홍삼 관련)을 찾지 못했습니다.")
        with open("fix_ginseng_post_results.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(_LOG))
        return

    log(f"대상 글: {target['title']['rendered']}")
    log(f"URL: {target['link']}")

    raw_content = target["content"].get("raw") or target["content"]["rendered"]
    cleaned = strip_code_fences(raw_content)

    # ★ 중복 이미지 수정: featured_media(대표이미지)와 본문 첫 인라인 이미지가
    #   완전히 동일한 파일이면(지난 수정 스크립트가 그렇게 저장함), 본문 쪽의
    #   중복 <figure><img> 블록을 제거한다 (대표이미지는 테마가 상단에 자동 노출하므로).
    dup_removed = False
    fig_match = re.search(r'<figure[^>]*>\s*<img[^>]+src="([^"]+)"[^>]*>.*?</figure>\s*', cleaned, re.DOTALL)
    if fig_match:
        img_src = fig_match.group(1)
        img_filename = img_src.rstrip('/').split('/')[-1]
        # featured_media 조회해서 같은 파일인지 확인
        fr = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts/{target['id']}", auth=auth,
                           params={"_fields": "featured_media"}, timeout=15)
        featured_id = fr.json().get("featured_media") if fr.status_code == 200 else None
        if featured_id:
            mr = requests.get(f"{SITE_URL}/wp-json/wp/v2/media/{featured_id}", auth=auth,
                               params={"_fields": "source_url"}, timeout=15)
            featured_src = mr.json().get("source_url", "") if mr.status_code == 200 else ""
            if featured_src.rstrip('/').split('/')[-1] == img_filename:
                cleaned = cleaned[:fig_match.start()] + cleaned[fig_match.end():]
                dup_removed = True
                log(f"중복 이미지 제거: 본문 인라인의 '{img_filename}' (대표이미지와 동일 파일)")

    r = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{target['id']}", auth=auth,
                       json={"content": cleaned.strip()}, timeout=30)
    if r.status_code in (200, 201):
        log(f"✅ 업데이트 성공: {target['link']} (중복이미지제거={dup_removed})")
    else:
        log(f"❌ 업데이트 실패 {r.status_code}: {r.text[:400]}")

    with open("fix_ginseng_post_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))

if __name__ == "__main__":
    main()
