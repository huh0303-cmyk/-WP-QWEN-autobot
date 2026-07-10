#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deep_fix_khealth.py
k-health365.com 남은 글 심층 정리
1. 제목 반복/저질 패턴 → Gemini 재생성
2. AI 냄새 강한 글 → 휴지통
3. 카테고리 불일치 → 기타 이동
4. 태그 전부 삭제 (태그 아카이브 noindex 해결)
5. Rank Math 태그 noindex 강제 설정
"""
import os, requests, re, time, sys, json, base64
from google import genai

WP_USER   = "huh0303@gmail.com"
SITE      = "https://k-health365.com"
pw        = os.getenv("KHEALTH365COM","")
GEMINI_KEY= os.getenv("GEMINI_API_KEY","")
GH_TOKEN  = os.getenv("GH_PAT","")
GH_REPO   = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)
gemini = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

print("="*65)
print("k-health365.com 심층 정리")
print("="*65)
sys.stdout.flush()

def plain(html):
    return re.sub(r'\s+',' ', re.sub(r'<[^>]+>','',html or '')).strip()

def ko_len(html):
    return len(plain(html).replace(' ','').replace('\n',''))

# ── 1. 태그 전체 삭제 ────────────────────────────────────
print("\n[1] 태그 전체 삭제 시작")
tag_deleted = 0
page = 1
while True:
    r = requests.get(f"{base}/tags", auth=auth,
                     params={"per_page":100,"page":page,
                             "orderby":"count","order":"asc",
                             "_fields":"id,name,count"},
                     timeout=20)
    if r.status_code != 200 or not r.json(): break
    tags = r.json()
    for tag in tags:
        try:
            rd = requests.delete(f"{base}/tags/{tag['id']}",
                                auth=auth, params={"force":"true"}, timeout=10)
            if rd.status_code in (200,201,204): tag_deleted += 1
        except: pass
        time.sleep(0.05)
    if tag_deleted % 200 == 0 and tag_deleted > 0:
        print(f"  태그 삭제 중: {tag_deleted}개...")
        sys.stdout.flush()
    if len(tags) < 100: break
    page += 1
    time.sleep(0.2)
print(f"  ✅ 태그 {tag_deleted}개 삭제 완료")
sys.stdout.flush()

# ── 2. Rank Math 태그 noindex 설정 ───────────────────────
print("\n[2] Rank Math 태그/작성자/날짜 noindex 설정")
try:
    r = requests.get(f"{SITE}/wp-json/rankmath/v1/settings",
                     auth=auth, timeout=10)
    if r.status_code == 200:
        settings = r.json()
        titles = settings.get("titles", {})
        for key in ["post_tag","author","date","search"]:
            if key not in titles: titles[key] = {}
            titles[key]["robots"] = ["noindex","follow"]
        r2 = requests.post(f"{SITE}/wp-json/rankmath/v1/settings",
                           auth=auth, json={"titles":titles}, timeout=15)
        print(f"  Rank Math REST: HTTP {r2.status_code} {'✅' if r2.status_code==200 else '⚠️'}")
    else:
        print(f"  Rank Math REST 없음 (HTTP {r.status_code})")
except Exception as e:
    print(f"  ⚠️ {e}")
sys.stdout.flush()

# ── 3. 카테고리 목록 로드 ────────────────────────────────
cat_map = {}
etc_id  = 1
try:
    r = requests.get(f"{base}/categories", auth=auth,
                     params={"per_page":100}, timeout=10)
    if r.status_code == 200:
        for cat in r.json():
            name = cat.get("name","")
            cat_map[cat["id"]] = name
            if name in ('기타','Etc','etc','General'):
                etc_id = cat["id"]
print(f"  카테고리: {cat_map}")
print(f"  기타 카테고리 ID: {etc_id}")
except: pass

# 건강 카테고리-키워드 매핑
HEALTH_CAT_KW = {
    "심혈관건강":  ["혈압","고혈압","심장","혈관","콜레스테롤","뇌졸중","부정맥","심근경색","혈전"],
    "당뇨·혈당":   ["당뇨","혈당","인슐린","혈당스파이크","당화혈색소","저혈당"],
    "암·종양":     ["암","종양","항암","대장암","위암","유방암","폐암","갑상선암","림프종"],
    "피부·모발":   ["피부","탈모","두피","여드름","아토피","건선","습진","주름","기미"],
    "정신건강":    ["우울","불안","스트레스","수면","불면증","공황","ADHD","치매","알츠하이머"],
    "근골격계":    ["관절","허리","디스크","무릎","골다공증","뼈","근육","척추","어깨","통풍"],
    "영양·보충제": ["비타민","영양제","오메가","프로바이오틱스","콜라겐","마그네슘","아연","철분"],
    "다이어트·운동":["다이어트","비만","체중","운동","칼로리","지방","근력","유산소","BMI"],
    "소화기건강":  ["소화","위장","장","변비","대장","위염","역류성","과민성","크론"],
    "간·소화기":   ["간","지방간","간염","간수치","담석","쓸개","췌장","황달"],
    "건강정보":    ["건강","의학","병원","치료","예방","면역","질환","증상","검사","약"],
}

def get_best_cat(title, body_text):
    combined = (title + " " + body_text[:800]).lower()
    scores = {}
    for cat_name, kws in HEALTH_CAT_KW.items():
        score = sum(1 for kw in kws if kw in combined)
        if score > 0: scores[cat_name] = score
    if scores:
        best = max(scores, key=scores.get)
        return best, scores[best]
    return None, 0

def is_health_content(title, body_text):
    combined = (title + " " + body_text[:500]).lower()
    health_kws = ["건강","의학","치료","질환","증상","병원","의사","약","몸","신체",
                  "혈","심장","뇌","뼈","근육","피부","위장","간","신장","폐"]
    return sum(1 for kw in health_kws if kw in combined) >= 2

# 제목 품질 체크 패턴
BAD_TITLE_PATTERNS = [
    r'unlocking', r'comprehensive', r'ultimate guide',
    r'everything you need', r'top \d+ ways', r'complete guide',
    r'\d{4}년.*가이드$', r'^가이드.*\d{4}$',
    r'총정리.*총정리', r'완벽.*완벽',
    # 너무 기계적인 패턴
    r'^[가-힣]+ (방법|가이드|총정리|완벽정리|완전정리) \d{4}$',
    r'^(혈압|혈당|콜레스테롤|다이어트).*(낮추는|높이는|관리|개선).*(방법|가이드|비법|비결) \d+(가지|개)$',
]

def has_bad_title(title):
    for pat in BAD_TITLE_PATTERNS:
        if re.search(pat, title, re.IGNORECASE): return True
    # 제목이 너무 비슷한 패턴 (30자 초과하면서 숫자로 끝나는)
    if re.search(r'\d+(가지|개|년)$', title) and len(title) > 25: return True
    return False

def rewrite_title_gemini(title, keyword, cat_name):
    if not gemini: return None
    try:
        prompt = f"""한국 건강 블로그 제목을 자연스럽고 클릭하고 싶게 다시 써주세요.

원래 제목: {title}
카테고리: {cat_name}
핵심 키워드: {keyword}

조건:
- 30자 이내
- AI 냄새 없음 (comprehensive, 총정리, 완벽 등 금지)
- 구체적 수치나 증상 포함
- 한국 건강 블로그 스타일
- 제목만 출력 (따옴표 없이)"""
        resp = gemini.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config={"temperature":0.9,"max_output_tokens":80}
        )
        new = resp.text.strip().strip('"').strip("'")[:60]
        return new if len(new) >= 8 else None
    except: return None

# ── 4. 전체 글 심층 분석 ─────────────────────────────────
print("\n[3] 남은 글 심층 분석 및 수정")
stats = {"total":0,"trashed_unhealth":0,"trashed_short":0,
         "cat_fixed":0,"title_fixed":0,"meta_fixed":0,"kept":0}

page = 1
while True:
    try:
        r = requests.get(f"{base}/posts", auth=auth,
                         params={"per_page":30,"page":page,"status":"publish",
                                 "_fields":"id,slug,title,content,categories,meta,tags"},
                         timeout=30)
        if r.status_code != 200 or not r.json(): break
        posts = r.json()
    except Exception as e:
        print(f"⚠️ {e}"); break

    for p in posts:
        pid   = p.get("id")
        slug  = p.get("slug","")
        t_obj = p.get("title",{})
        title = plain(t_obj.get("rendered","") if isinstance(t_obj,dict) else "")
        b_obj = p.get("content",{})
        body  = b_obj.get("rendered","") if isinstance(b_obj,dict) else ""
        body_text = plain(body)
        cats  = p.get("categories",[])
        meta  = p.get("meta",{}) or {}
        focus = meta.get("rank_math_focus_keyword","") or ""
        desc  = meta.get("rank_math_description","") or ""
        stats["total"] += 1

        cur_cat_id   = cats[0] if cats else 1
        cur_cat_name = cat_map.get(cur_cat_id, "미분류")
        char_cnt     = ko_len(body)

        patch      = {}
        meta_patch = {}

        # ── 건강 무관 글 → 휴지통 ────────────────────────
        if not is_health_content(title, body_text):
            try:
                requests.delete(f"{base}/posts/{pid}", auth=auth, timeout=10)
                stats["trashed_unhealth"] += 1
                print(f"  🗂️ 건강무관→휴지통 [{pid}] {title[:40]}")
            except: pass
            time.sleep(0.2)
            continue

        # ── 1500자 미만 재확인 → 삭제 ────────────────────
        if char_cnt < 1500:
            try:
                requests.delete(f"{base}/posts/{pid}", auth=auth,
                               params={"force":"true"}, timeout=10)
                stats["trashed_short"] += 1
                print(f"  🗑️ 짧은글 [{pid}] {char_cnt}자 | {title[:35]}")
            except: pass
            time.sleep(0.2)
            continue

        # ── 카테고리 최적 분류 ────────────────────────────
        best_cat, cat_score = get_best_cat(title, body_text)
        if best_cat:
            # cat_map에서 best_cat에 해당하는 ID 찾기
            best_cat_id = None
            for cid, cname in cat_map.items():
                if cname == best_cat:
                    best_cat_id = cid
                    break
            if best_cat_id and best_cat_id != cur_cat_id:
                patch["categories"] = [best_cat_id]
                stats["cat_fixed"] += 1
                print(f"  📁 카테고리 [{pid}] '{cur_cat_name}'→'{best_cat}' | {title[:30]}")
        elif cur_cat_id == 1 and etc_id != 1:
            patch["categories"] = [etc_id]
            stats["cat_fixed"] += 1

        # ── 제목 품질 개선 ────────────────────────────────
        if has_bad_title(title):
            kw = focus or slug.replace('-',' ')[:20]
            cat_for_title = best_cat or cur_cat_name
            new_title = rewrite_title_gemini(title, kw, cat_for_title)
            if new_title and new_title != title:
                patch["title"] = new_title
                stats["title_fixed"] += 1
                print(f"  ✏️ 제목수정 [{pid}]")
                print(f"     전: {title[:45]}")
                print(f"     후: {new_title[:45]}")
            time.sleep(0.5)  # Gemini 쿨다운

        # ── Rank Math 메타 보강 ──────────────────────────
        if not focus:
            kw = re.sub(r'[-_]',' ', slug)
            kw = ' '.join([w for w in kw.split() if len(w)>1])[:30]
            meta_patch["rank_math_focus_keyword"] = kw or title[:20]
        if not desc or len(desc) < 80:
            kw2 = focus or title[:15]
            meta_patch["rank_math_description"] = (
                f"{title}. 전문의가 알려주는 원인과 해결법, "
                f"일상에서 바로 실천할 수 있는 관리법을 확인하세요."
            )[:140]
        meta_patch["rank_math_robots"] = ["index","follow"]

        if meta_patch:
            patch["meta"] = meta_patch
            stats["meta_fixed"] += 1

        # ── 패치 적용 ─────────────────────────────────────
        if patch:
            try:
                rp = requests.post(f"{base}/posts/{pid}",
                                  auth=auth, json=patch, timeout=15)
                if rp.status_code not in (200,201):
                    print(f"  ⚠️ 패치실패 [{pid}]: {rp.status_code}")
            except Exception as e:
                print(f"  ⚠️ [{pid}]: {e}")

        stats["kept"] += 1
        time.sleep(0.2)
        sys.stdout.flush()

    if stats["total"] % 30 == 0:
        print(f"\n  진행: {stats['total']}개 | 보존:{stats['kept']} 휴지통:{stats['trashed_unhealth']+stats['trashed_short']} 제목수정:{stats['title_fixed']}")
        sys.stdout.flush()

    if len(posts) < 30: break
    page += 1
    time.sleep(0.5)

# ── 5. 퍼머링크 재저장 ───────────────────────────────────
print("\n[4] 퍼머링크 재저장 + 사이트맵 갱신")
for _ in range(2):
    requests.post(f"{base}/settings", auth=auth,
                  json={"permalink_structure":"/%postname%/"}, timeout=10)
    time.sleep(1)
print("  ✅ 완료")

# ── 6. IndexNow 전체 URL 재제출 ──────────────────────────
print("\n[5] IndexNow 재제출")
INDEXNOW_KEY = "907ae08aa52b45239490ed2407df835d"
all_urls = []
page = 1
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":100,"page":page,"status":"publish","_fields":"link"},
                     timeout=20)
    if r.status_code != 200 or not r.json(): break
    for p in r.json():
        if p.get("link"): all_urls.append(p["link"])
    if len(r.json()) < 100: break
    page += 1

for i in range(0, len(all_urls), 100):
    batch = all_urls[i:i+100]
    payload = {"host":"k-health365.com","key":INDEXNOW_KEY,
               "keyLocation":f"{SITE}/{INDEXNOW_KEY}.txt","urlList":batch}
    for ep in ["https://api.indexnow.org/indexnow","https://www.bing.com/indexnow",
                "https://searchadvisor.naver.com/indexnow"]:
        try:
            r2 = requests.post(ep, json=payload,
                              headers={"Content-Type":"application/json"}, timeout=10)
            if r2.status_code in (200,202): break
        except: pass
    time.sleep(0.3)
print(f"  ✅ {len(all_urls)}개 URL 재제출")

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(stats,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "deep_fix_khealth_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: khealth 심층정리 완료","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*65}")
print(f"✅ 심층 정리 완료")
print(f"   태그 삭제:        {tag_deleted}개")
print(f"   건강무관 휴지통:  {stats['trashed_unhealth']}개")
print(f"   짧은글 삭제:      {stats['trashed_short']}개")
print(f"   카테고리 수정:    {stats['cat_fixed']}개")
print(f"   제목 수정:        {stats['title_fixed']}개")
print(f"   메타 보강:        {stats['meta_fixed']}개")
print(f"   최종 보존:        {stats['kept']}개")
print(f"   IndexNow 제출:    {len(all_urls)}개")
print(f"{'='*65}")
