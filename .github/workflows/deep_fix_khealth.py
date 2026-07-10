#!/usr/bin/env python3
import os, requests, re, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")
if not pw: print("NO PW"); exit(1)

base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

def plain(html):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',html or '')).strip()

def ko_len(html):
    return len(plain(html).replace(' ','').replace('\n',''))

stats = {"tag_deleted":0,"trashed_unhealth":0,"trashed_short":0,
         "cat_fixed":0,"title_fixed":0,"meta_fixed":0,"kept":0,"indexnow":0}

print("="*60)
print("k-health365.com 심층 정리 (Gemini 없이)")
print("="*60); sys.stdout.flush()

# ── 1. 태그 전체 삭제 ────────────────────────────────────
print("\n[1] 태그 전체 삭제")
pg = 1
while True:
    r = requests.get(f"{base}/tags",auth=auth,
                     params={"per_page":100,"page":pg,"_fields":"id,count"},timeout=20)
    if r.status_code != 200 or not r.json(): break
    tags = r.json()
    for tag in tags:
        try:
            rd = requests.delete(f"{base}/tags/{tag['id']}",auth=auth,
                                params={"force":"true"},timeout=8)
            if rd.status_code in (200,201,204): stats["tag_deleted"]+=1
        except: pass
        time.sleep(0.04)
    if stats["tag_deleted"] % 300 == 0 and stats["tag_deleted"] > 0:
        print(f"  태그 삭제 중: {stats['tag_deleted']}개..."); sys.stdout.flush()
    if len(tags) < 100: break
    pg += 1; time.sleep(0.2)
print(f"  ✅ 태그 {stats['tag_deleted']}개 삭제"); sys.stdout.flush()

# ── 2. Rank Math 태그 noindex ────────────────────────────
print("\n[2] Rank Math 태그/작성자/날짜 noindex")
try:
    r = requests.get(f"{SITE}/wp-json/rankmath/v1/settings",auth=auth,timeout=10)
    if r.status_code == 200:
        s = r.json(); titles = s.get("titles",{})
        for key in ["post_tag","author","date","search"]:
            if key not in titles: titles[key]={}
            titles[key]["robots"]=["noindex","follow"]
        r2 = requests.post(f"{SITE}/wp-json/rankmath/v1/settings",
                           auth=auth,json={"titles":titles},timeout=15)
        print(f"  HTTP {r2.status_code} {'✅' if r2.status_code==200 else '⚠️'}")
except Exception as e:
    print(f"  ⚠️ {e}")
sys.stdout.flush()

# ── 3. 카테고리 로드 ─────────────────────────────────────
cat_map={}; etc_id=1
r = requests.get(f"{base}/categories",auth=auth,params={"per_page":100},timeout=10)
if r.status_code==200:
    for cat in r.json():
        cat_map[cat["id"]] = cat.get("name","")
        if cat.get("name","") in ('기타','Etc','etc','General'): etc_id=cat["id"]
print(f"\n  카테고리: {cat_map}")

HEALTH_CAT_KW = {
    "심혈관건강":  ["혈압","고혈압","심장","혈관","콜레스테롤","뇌졸중","심근경색"],
    "당뇨·혈당":   ["당뇨","혈당","인슐린","혈당스파이크","당화혈색소"],
    "암·종양":     ["암","종양","항암","대장암","위암","유방암","폐암","갑상선암"],
    "피부·모발":   ["피부","탈모","두피","여드름","아토피","건선","주름"],
    "정신건강":    ["우울","불안","스트레스","수면","불면증","공황","치매"],
    "근골격계":    ["관절","허리","디스크","무릎","골다공증","척추","어깨"],
    "영양·보충제": ["비타민","영양제","오메가","프로바이오틱스","콜라겐","마그네슘"],
    "다이어트·운동":["다이어트","비만","체중","운동","칼로리","지방","근력"],
    "소화기건강":  ["소화","위장","장","변비","대장","위염","역류","과민성"],
    "간·소화기":   ["간","지방간","간염","간수치","담석","췌장"],
}
HEALTH_KWS = ["건강","의학","치료","질환","증상","병원","의사","약","몸",
              "혈","심장","뇌","뼈","근육","피부","위장","간","신장","폐",
              "당뇨","혈압","암","영양","다이어트","수면","통증"]

BAD_TITLE_WORDS = [
    'unlocking','comprehensive','ultimate guide','everything you need',
    'complete guide','top ways','a complete','an ultimate',
]
def has_bad_title(title):
    tl = title.lower()
    for w in BAD_TITLE_WORDS:
        if w in tl: return True
    return False

def fix_title_simple(title, focus):
    """Gemini 없이 제목 정리 — 나쁜 패턴만 제거"""
    t = title
    for w in ['Unlocking ','Comprehensive Guide to ',
              'The Ultimate Guide to ','Everything You Need to Know About ',
              'A Complete Guide to ']:
        t = t.replace(w,'').replace(w.lower(),'')
    t = t.strip()
    if t == title: return None  # 변경 없으면 None
    return t[:60] if t else None

def best_category(title, body_text):
    combined = (title+" "+body_text[:600]).lower()
    scores={}
    for cat_name, kws in HEALTH_CAT_KW.items():
        sc = sum(1 for kw in kws if kw in combined)
        if sc>0: scores[cat_name]=sc
    return max(scores,key=scores.get) if scores else None

def is_health(title, body_text):
    combined=(title+" "+body_text[:400]).lower()
    return sum(1 for kw in HEALTH_KWS if kw in combined) >= 2

# ── 4. 글 처리 ───────────────────────────────────────────
print("\n[3] 글 전수 처리"); sys.stdout.flush()
pg=1
while True:
    try:
        r=requests.get(f"{base}/posts",auth=auth,
                       params={"per_page":30,"page":pg,"status":"publish",
                               "_fields":"id,slug,title,content,categories,meta"},
                       timeout=30)
        if r.status_code!=200 or not r.json(): break
        posts=r.json()
    except Exception as e:
        print(f"⚠️ {e}"); break

    for p in posts:
        pid  = p.get("id")
        slug = p.get("slug","")
        t_obj= p.get("title",{})
        title= plain(t_obj.get("rendered","") if isinstance(t_obj,dict) else "")
        b_obj= p.get("content",{})
        body = b_obj.get("rendered","") if isinstance(b_obj,dict) else ""
        bt   = plain(body)
        cats = p.get("categories",[])
        meta = p.get("meta",{}) or {}
        focus= meta.get("rank_math_focus_keyword","") or ""
        desc = meta.get("rank_math_description","") or ""
        cur_cid = cats[0] if cats else 1

        char_cnt = ko_len(body)
        patch={}; mpatch={}

        # 건강 무관 → 휴지통
        if not is_health(title, bt):
            try:
                requests.delete(f"{base}/posts/{pid}",auth=auth,timeout=10)
                stats["trashed_unhealth"]+=1
                print(f"  🗂️ 건강무관 [{pid}] {title[:40]}")
            except: pass
            time.sleep(0.2); continue

        # 1500자 미만 → 삭제
        if char_cnt < 1500:
            try:
                requests.delete(f"{base}/posts/{pid}",auth=auth,
                               params={"force":"true"},timeout=10)
                stats["trashed_short"]+=1
                print(f"  🗑️ 짧은글 [{pid}] {char_cnt}자")
            except: pass
            time.sleep(0.2); continue

        # 카테고리 재분류
        best=best_category(title,bt)
        if best:
            best_id=next((cid for cid,cn in cat_map.items() if cn==best),None)
            if best_id and best_id!=cur_cid:
                patch["categories"]=[best_id]
                stats["cat_fixed"]+=1
                print(f"  📁 [{pid}] →'{best}' | {title[:30]}")

        # 제목 정리
        if has_bad_title(title):
            new_t=fix_title_simple(title, focus)
            if new_t:
                patch["title"]=new_t
                stats["title_fixed"]+=1
                print(f"  ✏️ 제목 [{pid}] {title[:30]}→{new_t[:30]}")

        # 메타 보강
        if not focus:
            kw=re.sub(r'[-_]',' ',slug)
            kw=' '.join([w for w in kw.split() if len(w)>1])[:25]
            mpatch["rank_math_focus_keyword"]=kw or title[:20]
        if not desc or len(desc)<80:
            mpatch["rank_math_description"]=(
                f"{title}. 전문의가 알려주는 핵심 원인과 관리법, "
                f"일상에서 바로 실천할 수 있는 건강 정보를 확인하세요."
            )[:140]
        mpatch["rank_math_robots"]=["index","follow"]
        if mpatch:
            patch["meta"]=mpatch
            stats["meta_fixed"]+=1

        if patch:
            try:
                rp=requests.post(f"{base}/posts/{pid}",auth=auth,
                                json=patch,timeout=15)
            except: pass

        stats["kept"]+=1
        time.sleep(0.15)

    if stats["kept"] % 30 == 0:
        print(f"  진행: 보존{stats['kept']} 휴지통{stats['trashed_unhealth']+stats['trashed_short']}")
        sys.stdout.flush()

    if len(posts)<30: break
    pg+=1; time.sleep(0.3)

# ── 5. IndexNow 재제출 ───────────────────────────────────
print("\n[4] IndexNow 재제출")
KEY="907ae08aa52b45239490ed2407df835d"
urls=[]; pg=1
while True:
    r=requests.get(f"{base}/posts",auth=auth,
                   params={"per_page":100,"page":pg,"status":"publish","_fields":"link"},
                   timeout=20)
    if r.status_code!=200 or not r.json(): break
    for p in r.json():
        if p.get("link"): urls.append(p["link"])
    if len(r.json())<100: break
    pg+=1
for i in range(0,len(urls),100):
    batch=urls[i:i+100]
    payload={"host":"k-health365.com","key":KEY,
             "keyLocation":f"{SITE}/{KEY}.txt","urlList":batch}
    for ep in ["https://api.indexnow.org/indexnow","https://www.bing.com/indexnow",
                "https://searchadvisor.naver.com/indexnow"]:
        try:
            r2=requests.post(ep,json=payload,
                            headers={"Content-Type":"application/json"},timeout=10)
            if r2.status_code in (200,202): break
        except: pass
    time.sleep(0.3)
stats["indexnow"]=len(urls)
print(f"  ✅ {len(urls)}개 URL 제출")

# 결과 저장
if GH_TOKEN:
    content=base64.b64encode(json.dumps(stats,ensure_ascii=False,indent=2).encode()).decode()
    gh_h={"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path="deep_fix_khealth_result.json"
    rg=requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha=rg.json().get("sha","") if rg.status_code==200 else ""
    payload={"message":"result: khealth 심층정리","content":content}
    if sha: payload["sha"]=sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"   태그삭제:    {stats['tag_deleted']}")
print(f"   건강무관:    {stats['trashed_unhealth']}")
print(f"   짧은글:      {stats['trashed_short']}")
print(f"   카테고리:    {stats['cat_fixed']}")
print(f"   제목수정:    {stats['title_fixed']}")
print(f"   메타보강:    {stats['meta_fixed']}")
print(f"   최종보존:    {stats['kept']}")
print(f"{'='*60}")
