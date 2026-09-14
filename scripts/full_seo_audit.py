#!/usr/bin/env python3
"""
k-health365.com 전체 글 SEO 전수 감사
- 2500자 미만 → 삭제 대상
- URL 끝 숫자 패턴 (Blogger 이전 글) → 별도 분류
- SEO 점수 80점 미만 → 휴지통 대상
- 제목 중복/반복 → 수정 대상
- 결과 JSON 저장
"""
import os, requests, re, json, base64, time

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

def plain(html):
    return re.sub(r'\s+',' ', re.sub(r'<[^>]+>','',html or '')).strip()

def char_count(html):
    return len(plain(html).replace(' ','').replace('\n',''))

def seo_score(title, body, desc, focus):
    s = 0
    chars = char_count(body)
    if chars >= 3500: s += 30
    elif chars >= 2500: s += 22
    elif chars >= 2000: s += 14
    elif chars >= 1500: s += 8
    if title and 15 <= len(title) <= 55: s += 12
    if desc and len(desc) >= 100: s += 15
    elif desc: s += 5
    if focus: s += 10
    h2 = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    tb = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    ul = len(re.findall(r'<ul[\s>]', body, re.IGNORECASE))
    if h2 >= 4: s += 12
    elif h2 >= 2: s += 6
    if tb >= 1: s += 8
    if ul >= 2: s += 5
    nums = len(re.findall(r'\d+[\.,]?\d*\s*(?:%|명|만|원|mmHg|mg)', body))
    if nums >= 5: s += 8
    return min(s, 100)

def is_blogger_url(slug):
    """Blogger 이전 글 패턴: 끝이 숫자 or blog-post_숫자"""
    return bool(re.search(r'[-_]\d+$', slug) or
                re.match(r'^blog-post', slug) or
                re.match(r'^\d{4}[-_]', slug))

# 전체 글 수집
all_posts = []
page = 1
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":50,"page":page,"status":"publish",
                             "_fields":"id,slug,title,content,meta,date,categories"},
                     timeout=30)
    if r.status_code != 200 or not r.json(): break
    for p in r.json():
        slug  = p.get("slug","")
        t_obj = p.get("title",{})
        title = plain(t_obj.get("rendered","") if isinstance(t_obj,dict) else "")
        b_obj = p.get("content",{})
        body  = b_obj.get("rendered","") if isinstance(b_obj,dict) else ""
        meta  = p.get("meta",{}) or {}
        desc  = meta.get("rank_math_description","") or ""
        focus = meta.get("rank_math_focus_keyword","") or ""
        chars = char_count(body)
        score = seo_score(title, body, desc, focus)
        blogger = is_blogger_url(slug)

        all_posts.append({
            "id":      p["id"],
            "slug":    slug,
            "title":   title[:60],
            "chars":   chars,
            "score":   score,
            "blogger": blogger,
            "date":    p.get("date","")[:10],
            "has_focus": bool(focus),
            "has_desc":  bool(desc),
            "h2_count":  len(re.findall(r'<h2[\s>]', body, re.IGNORECASE)),
            "table_count": len(re.findall(r'<table[\s>]', body, re.IGNORECASE)),
        })
    if len(r.json()) < 50: break
    page += 1
    time.sleep(0.3)

# 분류
delete_short  = [p for p in all_posts if p["chars"] < 2500]
trash_seo     = [p for p in all_posts if p["chars"] >= 2500 and p["score"] < 80]
blogger_posts = [p for p in all_posts if p["blogger"]]
good_posts    = [p for p in all_posts if p["chars"] >= 2500 and p["score"] >= 80]
no_focus      = [p for p in all_posts if not p["has_focus"] and p["chars"] >= 2500]
no_desc       = [p for p in all_posts if not p["has_desc"] and p["chars"] >= 2500]

print(f"{'='*60}")
print(f"k-health365.com SEO 전수 감사 결과")
print(f"{'='*60}")
print(f"총 글 수: {len(all_posts)}개")
print(f"")
print(f"🗑️  삭제 (2500자 미만):  {len(delete_short)}개")
print(f"🗂️  휴지통 (SEO 80점 미만): {len(trash_seo)}개")
print(f"📝 Blogger 이전 글:    {len(blogger_posts)}개")
print(f"✅ 정상 (2500자+80점+): {len(good_posts)}개")
print(f"⚠️  focus keyword 없음: {len(no_focus)}개")
print(f"⚠️  meta desc 없음:     {len(no_desc)}개")

print(f"\n--- 삭제 대상 (2500자 미만) ---")
for p in sorted(delete_short, key=lambda x: x["chars"]):
    print(f"  [{p['id']}] {p['chars']}자 | {p['title'][:45]}")

print(f"\n--- SEO 휴지통 대상 (80점 미만) ---")
for p in sorted(trash_seo, key=lambda x: x["score"]):
    print(f"  [{p['id']}] {p['score']}점/{p['chars']}자 | {p['title'][:45]}")

print(f"\n--- Blogger 이전 글 (초창기, 슬러그 숫자 패턴) ---")
for p in sorted(blogger_posts, key=lambda x: x["date"]):
    status = "✅좋음" if p["score"] >= 80 else f"⚠️{p['score']}점"
    print(f"  [{p['id']}] {status} {p['chars']}자 | {p['title'][:40]} | {p['date']}")

# 저장
result = {
    "total": len(all_posts),
    "delete_short": [{"id":p["id"],"slug":p["slug"],"chars":p["chars"],"title":p["title"]} for p in delete_short],
    "trash_seo": [{"id":p["id"],"slug":p["slug"],"score":p["score"],"title":p["title"]} for p in trash_seo],
    "blogger_posts": [{"id":p["id"],"slug":p["slug"],"score":p["score"],"chars":p["chars"],"title":p["title"],"date":p["date"]} for p in blogger_posts],
    "good_posts_count": len(good_posts),
    "no_focus_count":   len(no_focus),
    "no_desc_count":    len(no_desc),
}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_seo_audit.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"audit: khealth SEO 전수 감사","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)
print("\n저장 완료")
