#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_content.py
k-health365.com 콘텐츠 전수 정리
1. 1500자 미만 → 삭제
2. AI냄새 패턴 감지 → Gemini로 재생성
3. 카테고리-내용 불일치 → 기타로 이동
4. SEO 80점 미만 → 휴지통
5. 색인 최적화 (Rank Math 메타 보강)
"""
import os, requests, re, time, sys, json, base64
from google import genai

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GEMINI_KEY = os.getenv("GEMINI_API_KEY","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)

base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

gemini = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

print("="*65)
print("k-health365.com 콘텐츠 전수 정리")
print("="*65)
sys.stdout.flush()

def plain(html):
    t = re.sub(r'<[^>]+>', '', html or '')
    return re.sub(r'\s+', ' ', t).strip()

def ko_char_count(html):
    """한글 기준 글자 수"""
    text = plain(html)
    return len(text.replace(' ','').replace('\n',''))

def has_ai_smell(title, body):
    """AI 냄새 패턴 감지"""
    text = plain(body).lower()
    title_l = title.lower()

    patterns = [
        # 제목 패턴
        r'unlocking', r'comprehensive guide', r'everything you need',
        r'ultimate guide', r'complete guide to',
        # 본문 패턴
        r'in this article.*we will', r'in conclusion.*overall',
        r'it is important to note', r'it is worth noting',
        r'as (an|a) ai', r'i cannot', r'i do not have',
        r'furthermore.*moreover.*additionally',
        r'첫째.*둘째.*셋째',
        r'이 글에서는.*살펴보겠습니다',
        r'마지막으로.*정리하면',
    ]
    smell_count = 0
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE): smell_count += 1
        if re.search(pat, title_l, re.IGNORECASE): smell_count += 2

    # 반복 구조 체크 (h2가 너무 획일적)
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', body, re.IGNORECASE|re.DOTALL)
    h2_texts = [plain(h).lower() for h in h2s]
    generic_h2 = sum(1 for h in h2_texts if any(
        x in h for x in ['introduction','conclusion','overview','summary',
                          '소개','결론','개요','요약','마치며']
    ))
    if generic_h2 >= 2: smell_count += 2

    return smell_count >= 2, smell_count

def estimate_seo(title, body, meta_desc, focus_kw):
    score = 0
    plain_b = plain(body)
    blen = len(plain_b.replace(' ','').replace('\n',''))
    if blen >= 3000: score += 25
    elif blen >= 2000: score += 18
    elif blen >= 1500: score += 12
    elif blen >= 800:  score += 5
    if title and 10 <= len(title) <= 65: score += 12
    if meta_desc and len(meta_desc) >= 100: score += 15
    elif meta_desc: score += 5
    if focus_kw: score += 10
    h2 = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    tb = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    ul = len(re.findall(r'<ul[\s>]', body, re.IGNORECASE))
    if h2 >= 4: score += 12
    elif h2 >= 2: score += 6
    if tb >= 1: score += 8
    if ul >= 2: score += 5
    stats = len(re.findall(r'\d+[\.,]?\d*\s*(?:%|명|만|억|원|mmHg|mg|kg|kcal)', body))
    if stats >= 5: score += 8
    elif stats >= 2: score += 4
    links = len(re.findall(r'<a\s+href=["\']https?://', body, re.IGNORECASE))
    if links >= 4: score += 5
    return min(score, 100)

# 카테고리 목록 로드
cat_map = {}
try:
    r = requests.get(f"{base}/categories", auth=auth,
                     params={"per_page":100}, timeout=10)
    if r.status_code == 200:
        for cat in r.json():
            cat_map[cat["id"]] = cat.get("name","")
    print(f"카테고리: {cat_map}")
except: pass

# 기타 카테고리 ID
etc_id = None
for cid, cname in cat_map.items():
    if cname in ('기타','Etc','etc','General','Uncategorized','미분류'):
        etc_id = cid
        break
if not etc_id: etc_id = 1

# 건강 카테고리 키워드 매핑
HEALTH_KEYWORDS = {
    '심혈관건강': ['혈압','심장','혈관','콜레스테롤','뇌졸중','심근경색'],
    '당뇨·혈당': ['당뇨','혈당','인슐린','혈당스파이크'],
    '피부·모발': ['피부','탈모','두피','여드름','아토피'],
    '정신건강': ['우울','불안','스트레스','수면','불면','정신'],
    '근골격계': ['관절','허리','디스크','무릎','골다공증','뼈'],
    '영양·보충제': ['비타민','영양제','오메가','프로바이오틱스','콜라겐'],
    '다이어트·운동': ['다이어트','비만','체중','운동','칼로리'],
    '소화기건강': ['소화','위장','장','변비','대장','위'],
    '간·소화기': ['간','지방간','간염','간수치'],
    '암·종양': ['암','종양','항암'],
}

def detect_correct_category(title, body_text, current_cat_name):
    """카테고리 적합성 검사"""
    combined = (title + ' ' + body_text[:500]).lower()
    for cat_name, keywords in HEALTH_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return cat_name, True
    # 건강 관련 키워드가 전혀 없으면 부적합
    health_general = ['건강','의학','치료','질환','증상','병원','의사','약','몸','신체']
    for kw in health_general:
        if kw in combined:
            return current_cat_name, True
    return '기타', False

# ── 전체 글 처리 ─────────────────────────────────────────
page = 1
stats = {
    "total":0, "deleted_short":0, "trashed_seo":0,
    "cat_moved":0, "meta_fixed":0, "kept":0, "ai_smell":0
}

while True:
    try:
        r = requests.get(f"{base}/posts", auth=auth,
                         params={"per_page":30,"page":page,"status":"publish",
                                 "_fields":"id,slug,title,content,categories,meta"},
                         timeout=30)
        if r.status_code != 200 or not r.json(): break
        posts = r.json()
    except Exception as e:
        print(f"⚠️ 페이지{page} 오류: {e}"); break

    for p in posts:
        pid  = p.get("id")
        slug = p.get("slug","")
        t_obj = p.get("title",{})
        title = plain(t_obj.get("rendered","") if isinstance(t_obj,dict) else "")
        b_obj = p.get("content",{})
        body  = b_obj.get("rendered","") if isinstance(b_obj,dict) else ""
        body_text = plain(body)
        cats  = p.get("categories",[])
        meta  = p.get("meta",{}) or {}
        focus = meta.get("rank_math_focus_keyword","")
        desc  = meta.get("rank_math_description","")

        stats["total"] += 1
        char_count = ko_char_count(body)
        seo_score  = estimate_seo(title, body, desc, focus)
        ai_smell, smell_cnt = has_ai_smell(title, body)
        current_cat = cat_map.get(cats[0] if cats else 1, "미분류")

        # ── 1. 1500자 미만 → 삭제 ────────────────────────
        if char_count < 1500:
            try:
                rd = requests.delete(f"{base}/posts/{pid}",auth=auth,
                                    params={"force":"true"},timeout=10)
                if rd.status_code in (200,201,204,410):
                    stats["deleted_short"]+=1
                    print(f"  🗑️ 짧은글삭제 [{pid}] {char_count}자 | {title[:35]}")
            except: pass
            time.sleep(0.2)
            continue

        # ── 2. SEO 80점 미만 → 휴지통 ────────────────────
        if seo_score < 80:
            try:
                rt = requests.delete(f"{base}/posts/{pid}",auth=auth,timeout=10)
                if rt.status_code in (200,201):
                    stats["trashed_seo"]+=1
                    print(f"  🗂️ SEO휴지통 [{pid}] {seo_score}점 | {title[:35]}")
            except: pass
            time.sleep(0.2)
            continue

        # ── 3. 카테고리 불일치 → 기타 이동 ──────────────
        correct_cat, is_match = detect_correct_category(title, body_text, current_cat)
        patch = {}
        if not is_match:
            patch["categories"] = [etc_id]
            stats["cat_moved"]+=1
            print(f"  📁 카테고리이동 [{pid}] '{current_cat}'→기타 | {title[:30]}")

        # ── 4. AI냄새 제목 수정 (제목만 바꿈) ────────────
        if ai_smell and gemini:
            try:
                prompt = f"""한국어 건강 블로그 글 제목을 다시 써주세요.
기존 제목: {title}
조건: AI 냄새 없음, 30자 이내, 구체적 수치나 효과 포함, 클릭하고 싶은 제목
출력: 제목만"""
                resp = gemini.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"temperature":0.9,"max_output_tokens":100}
                )
                new_title = resp.text.strip().strip('"').strip("'")[:80]
                if new_title and len(new_title) >= 10:
                    patch["title"] = new_title
                    stats["ai_smell"]+=1
                    print(f"  ✏️ 제목수정 [{pid}] {title[:25]}→{new_title[:25]}")
            except: pass

        # ── 5. Rank Math 메타 보강 ────────────────────────
        meta_patch = {}
        if not focus:
            kw = slug.replace('-',' ')[:30]
            meta_patch["rank_math_focus_keyword"] = kw
        if not desc:
            meta_patch["rank_math_description"] = f"{title}. 전문의가 알려주는 핵심 정보와 일상 실천법을 확인하세요."[:140]
        meta_patch["rank_math_robots"] = ["index","follow"]
        if meta_patch:
            patch["meta"] = meta_patch
            stats["meta_fixed"]+=1

        # 패치 적용
        if patch:
            try:
                rp = requests.post(f"{base}/posts/{pid}",auth=auth,
                                  json=patch,timeout=15)
                if rp.status_code not in (200,201):
                    print(f"  ⚠️ 패치실패 [{pid}]: {rp.status_code}")
            except Exception as e:
                print(f"  ⚠️ [{pid}]: {e}")

        stats["kept"]+=1
        time.sleep(0.15)

    print(f"  [페이지{page}완료] 누적: 총{stats['total']} 삭제{stats['deleted_short']} 휴지통{stats['trashed_seo']} 보존{stats['kept']}")
    sys.stdout.flush()
    if len(posts) < 30: break
    page += 1
    time.sleep(1)

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(stats,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_cleanup_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: khealth 콘텐츠 정리","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*65}")
print(f"✅ k-health365.com 정리 완료")
print(f"   총 처리:        {stats['total']}개")
print(f"   1500자미만 삭제: {stats['deleted_short']}개")
print(f"   SEO80점미만 휴지통: {stats['trashed_seo']}개")
print(f"   카테고리 이동:  {stats['cat_moved']}개")
print(f"   AI제목 수정:    {stats['ai_smell']}개")
print(f"   메타 보강:      {stats['meta_fixed']}개")
print(f"   최종 보존:      {stats['kept']}개")
print(f"{'='*65}")
