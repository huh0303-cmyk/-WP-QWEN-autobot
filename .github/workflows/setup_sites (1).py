#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_sites.py — 27개 사이트 완전 정리 스크립트
위치: .github/workflows/setup_sites.py
실행: GitHub Actions [site-setup] job

작업 내역:
  [1] 카테고리 정리 — 황금 3개만 남기고 나머지 전부 삭제
  [2] 기존 포스트 → 황금 3개 카테고리로 자동 재배분
  [3] 불필요 페이지 삭제 → 필수 4페이지만 유지/생성
      (Privacy Policy / Disclaimer / Contact / About)
  [4] 색인 차단 해제 (noindex / robots)
  [5] 사이트명 정상화
  [6] 메뉴 정리 — 황금 3개 카테고리만 등록
"""

import os, time, re, requests

WP_USER = "huh0303@gmail.com"

# ── 필수 4페이지 slug (이것만 남기고 나머지 삭제) ────────────
KEEP_PAGE_SLUGS = {"privacy-policy", "disclaimer", "contact", "about"}

# ── 필수 4페이지 내용 ─────────────────────────────────────────
def required_pages(lang):
    if lang == "ko":
        return [
            ("개인정보처리방침", "privacy-policy",
             "<h2>개인정보처리방침</h2>"
             "<p>본 사이트는 이용자의 개인정보를 중요하게 여기며 관련 법령에 따라 보호합니다.</p>"
             "<ul><li>수집 항목: 이메일(문의 시), 방문 기록(분석 도구)</li>"
             "<li>이용 목적: 서비스 제공 및 통계 분석</li>"
             "<li>보유 기간: 이용 종료 후 즉시 파기</li></ul>"
             "<p>문의: huh0303@gmail.com</p>"),
            ("면책공고", "disclaimer",
             "<h2>면책공고</h2>"
             "<p>본 사이트의 정보는 참고 목적으로만 제공됩니다.</p>"
             "<p>정보의 정확성을 보장하지 않으며 전문적 조언이 필요한 경우 관련 전문가와 상담하시기 바랍니다.</p>"),
            ("문의하기", "contact",
             "<h2>문의하기</h2>"
             "<p>이메일: huh0303@gmail.com</p>"
             "<p>응답 시간: 영업일 기준 1~2일 이내</p>"),
            ("사이트 소개", "about",
             "<h2>사이트 소개</h2>"
             "<p>한국에 관심 있는 분들을 위한 전문 정보 블로그입니다.</p>"
             "<p>정확하고 유용한 정보를 꾸준히 제공합니다. 문의: huh0303@gmail.com</p>"),
        ]
    return [
        ("Privacy Policy", "privacy-policy",
         "<h2>Privacy Policy</h2>"
         "<p>We are committed to protecting your privacy in compliance with applicable laws.</p>"
         "<ul><li>Information collected: Email (contact form), visit logs (analytics)</li>"
         "<li>Purpose: Service delivery and improvement</li>"
         "<li>Retention: Deleted upon service termination</li></ul>"
         "<p>Contact: huh0303@gmail.com</p>"),
        ("Disclaimer", "disclaimer",
         "<h2>Disclaimer</h2>"
         "<p>All content on this site is for educational and informational purposes only.</p>"
         "<p>We make no warranties about accuracy. Please consult a qualified professional for advice.</p>"),
        ("Contact Us", "contact",
         "<h2>Contact Us</h2>"
         "<p>Email: huh0303@gmail.com</p>"
         "<p>Response time: Within 1-2 business days</p>"),
        ("About Us", "about",
         "<h2>About Us</h2>"
         "<p>This is a professional information blog about Korea.</p>"
         "<p>We provide accurate and useful content on a regular basis. Contact: huh0303@gmail.com</p>"),
    ]

# ════════════════════════════════════════════════════════════
# 27개 사이트 황금 카테고리 + 포스트 분류 키워드
# (url, env_key, lang, site_title,
#  cat1, cat2, cat3,
#  cat1_kws, cat2_kws,   ← 키워드 매칭 (나머지는 cat1 기본)
#  fix_index)
# ════════════════════════════════════════════════════════════
SITES = [
  ("https://k-health365.com","KHEALTH365COM","ko","K-Health365 건강정보",
   "건강의학정보","건강기능식품정보","질환별관리법",
   ["영양제","비타민","유산균","보충제","기능성","콜라겐","오메가","다이어트","체중","식품"],
   ["혈압","당뇨","혈당","암","피부","아토피","탈모","관절","허리","디스크","골다공증","수면","불면","우울","치료","예방","관리"],
   False),

  ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM","en","Korea Medical Tour",
   "Surgery","Dental","Dermatology",
   ["dental","teeth","orthodontics","implant","whitening","gum"],
   ["dermatology","skin","laser","botox","filler","acne","pigmentation","aesthetics"],
   False),

  ("https://koreainvest365.com","KOREAINVEST365COM","en","Korea Invest 365",
   "Stocks","Real Estate","Funds",
   ["real estate","property","apartment","jeonse","housing","land"],
   ["ETF","fund","mutual","index fund","bond","DeFi","crypto","bitcoin"],
   False),

  ("https://ki-korea.com","KIKOREACOM","ko","KI Korea 한국투자",
   "주식","부동산","절세",
   ["부동산","아파트","청약","분양","전세","토지","리츠"],
   ["절세","세금","IRP","연금","비과세","공제","ETF","펀드"],
   False),

  ("https://koreainsurance365.com","KOREAINSURANCE365COM","en","Korea Insurance 365",
   "Health Insurance","Life Insurance","Auto Insurance",
   ["life","death","term","whole life","accident","cancer insurance"],
   ["car","auto","vehicle","driver","traffic"],
   False),

  ("https://kfinance365.com","KFINANCE365COM","en","Korea Finance 365",
   "Banking","Investing","Taxes",
   ["invest","stock","ETF","portfolio","dividend","fund","crypto"],
   ["tax","income tax","VAT","refund","deduction","filing"],
   False),

  ("https://koreataxnlaw.com","KOREATAXNLAWCOM","en","Korea Tax & Law",
   "Taxes","Business","Visas",
   ["business","company","startup","registration","corporate","CEO","entrepreneur"],
   ["visa","immigration","residence","permit","foreigner","alien"],
   False),

  ("https://koreacrypto365.com","KOREACRYPTO365COM","en","Korea Crypto 365",
   "Bitcoin","Exchanges","Regulation",
   ["exchange","upbit","bithumb","binance","trading","buy","sell"],
   ["regulation","law","FSC","SEC","tax","legal","compliance"],
   False),

  ("https://krealestate365.com","KREALESTATE365COM","ko","한국부동산 정석",
   "아파트","투자","세금",
   ["투자","전략","수익","리츠","경매","법인","갭투자"],
   ["세금","취득세","양도세","재산세","증여","상속","절세"],
   True),   # robots 해제

  ("https://ktech365.com","KTECH365COM","en","KTech365 Korea Tech",
   "AI","Startups","Semiconductors",
   ["startup","venture","unicorn","investment","founder","funding","scale"],
   ["semiconductor","chip","TSMC","fab","wafer","memory","DRAM","NAND"],
   False),

  ("https://kskin365.com","KSKIN365COM","en","KSkin365 K-Beauty",
   "Skincare","Ingredients","Routines",
   ["ingredient","niacinamide","hyaluronic","retinol","vitamin C","peptide","ceramide"],
   ["routine","steps","morning","night","AM PM","order","layering"],
   False),

  ("https://oliveyoungkorea.com","OLIVEYOUNGKOREACOM","en","Olive Young Korea",
   "Skincare","Makeup","Haircare",
   ["makeup","foundation","lipstick","blush","eyeshadow","concealer","mascara"],
   ["hair","shampoo","scalp","conditioner","treatment","keratin"],
   False),

  ("https://kworld365.com","KWORLD365COM","en","KWorld365 K-POP",
   "Artists","Music","Tours",
   ["album","release","comeback","single","MV","track","playlist","music"],
   ["concert","tour","performance","live","show","event","stadium"],
   True),   # robots 해제

  ("https://k-trip365.com","KTRIP365COM","en","K-Trip365 Korea Travel",
   "Travel Guides","Food","Hotels",
   ["food","restaurant","cuisine","street food","dish","eat","cafe","coffee"],
   ["hotel","accommodation","stay","hostel","guesthouse","airbnb","pension"],
   False),

  ("https://k-visa365.com","KVISA365COM","en","K-Visa365 Korea Visa",
   "Work Visa","Student Visa","Long-term Visa",
   ["student","D-2","D-4","language school","university","study"],
   ["F-2","F-5","long-term","permanent","settlement","naturalization"],
   False),

  ("https://koreawedding365.com","KOREAWEDDING365COM","en","Korea Wedding 365",
   "Planning","Venues","Legal",
   ["venue","hall","location","ceremony","outdoor","garden","rooftop"],
   ["legal","registration","document","certificate","marriage law","registry"],
   False),

  ("https://kstudy365.com","KSTUDY365COM","en","KStudy365 Study in Korea",
   "Study Korea","Scholarships","Student Life",
   ["scholarship","GKS","KGSP","funding","stipend","tuition waiver","award"],
   ["student life","campus","dorm","dormitory","visa","part-time","adjustment"],
   False),

  ("https://studyinkorea365.com","STUDYINKOREA365COM","en","Study in Korea 365",
   "Admissions","Scholarships","Campus Life",
   ["scholarship","GKS","government","KGSP","funding","stipend","financial aid"],
   ["campus","dormitory","housing","student life","clubs","activities","adjustment"],
   False),

  ("https://kieca-korea.org","KIECAKOREAORG","en","KIECA Korea",
   "Language","Culture","Careers",
   ["culture","tradition","exchange","festival","history","art","heritage"],
   ["career","job","work","internship","employment","graduate"],
   False),

  ("https://ksa-korea.org","KSAKOREAORG","ko","KSA Korea 한국유학협회",
   "입학정보","장학금","비자",
   ["장학금","GKS","정부초청","지원금","면제","재정"],
   ["비자","D-2","출입국","체류","연장","HiKorea"],
   True),   # noindex 해제

  ("https://sis-korea.com","SISKOREACOM","en","SIS Korea",
   "Programs","Scholarships","TOPIK",
   ["scholarship","fee","funding","financial","tuition","cost"],
   ["TOPIK","Korean test","language exam","proficiency","level","test prep"],
   False),

  ("https://jobkorea365.com","JOBKOREA365COM","en","Job Korea 365",
   "Jobs","Salaries","Work Visa",
   ["salary","wage","income","pay","compensation","benefits","allowance"],
   ["visa","E-7","work permit","eligibility","sponsor","D-10"],
   False),

  ("https://jobinkorea365.com","JOBINKOREA365COM","en","Jobs in Korea 365",
   "Jobs","Interviews","Salaries",
   ["interview","preparation","question","answer","tips","STAR","behavioral"],
   ["salary","wage","negotiation","pay","compensation","raise","package"],
   False),

  ("https://jobkoreaglobal.com","JOBKOREAGLOBALCOM","en","Job Korea Global",
   "Hiring","Salaries","Foreign Workers",
   ["salary","compensation","benefits","pay scale","benchmark","raise"],
   ["foreign worker","EPS","H-2","E-9","migrant","overseas","international hire"],
   False),

  ("https://korea365.org","KOREA365ORG","en","Korea 365",
   "Korean Culture","Travel & Food","Living in Korea",
   ["travel","food","restaurant","cuisine","trip","destination","tourism","sightseeing"],
   ["living","expat","foreigner","daily","tips","cost","apartment","transport"],
   False),

  ("https://koreanews365.com","KOREANEWS365COM","ko","한국타임즈",
   "경제","정치","사회",
   ["정치","대통령","국회","선거","외교","북한","여당","야당","법안"],
   ["사회","범죄","복지","교육","문화","국제","IT","반도체","스타트업"],
   False),

  ("https://theseouljournal.com","THESEOULJOURNALCOM","en","The Seoul Journal",
   "Politics","Economy","Culture",
   ["economy","market","stock","trade","business","startup","finance","GDP","inflation"],
   ["culture","K-pop","music","food","lifestyle","travel","expat","entertainment"],
   False),
]

# ════════════════════════════════════════════════════════════
# API 유틸
# ════════════════════════════════════════════════════════════
def api(method, url, pw, data=None, params=None):
    try:
        r = requests.request(
            method, url,
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json=data, params=params,
            headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"},
            timeout=20, verify=True
        )
        try:
            body = r.json()
        except Exception:
            body = {}
        return r.status_code, body, r.headers
    except Exception as e:
        return 0, {"error": str(e)[:80]}, {}

# ── 카테고리 전체 조회 ─────────────────────────────────────
def get_all_cats(base, pw):
    cats = []
    page = 1
    while True:
        code, r, _ = api("GET", f"{base}/categories", pw,
                          params={"per_page":100,"page":page})
        if code != 200 or not isinstance(r, list) or not r:
            break
        cats.extend(r)
        if len(r) < 100:
            break
        page += 1
    return cats

# ── 카테고리 생성/조회 ─────────────────────────────────────
def get_or_create_cat(base, pw, name, slug):
    code, r, _ = api("GET", f"{base}/categories", pw,
                      params={"slug": slug, "per_page":1})
    if isinstance(r, list) and r:
        return r[0]["id"]
    code, r, _ = api("POST", f"{base}/categories", pw,
                      {"name": name, "slug": slug,
                       "description": f"{name} category"})
    if code in (200,201) and r.get("id"):
        print(f"    ✅ 카테고리 생성: {name}")
        return r["id"]
    # 이름으로 검색
    code, r, _ = api("GET", f"{base}/categories", pw,
                      params={"search": name, "per_page":10})
    if isinstance(r, list):
        for c in r:
            if c.get("name","").strip().lower() == name.strip().lower():
                return c["id"]
    print(f"    ⚠️ 카테고리 생성 실패: {name}")
    return None

# ── 카테고리 삭제 ──────────────────────────────────────────
def delete_cat(base, pw, cat_id):
    code, _, _ = api("DELETE", f"{base}/categories/{cat_id}",
                     pw, params={"force": True})
    return code in (200, 201)

# ── 페이지 전체 조회 ───────────────────────────────────────
def get_all_pages(base, pw):
    pages = []
    page = 1
    while True:
        code, r, _ = api("GET", f"{base}/pages", pw,
                          params={"per_page":100,"page":page,"status":"any"})
        if code != 200 or not isinstance(r, list) or not r:
            break
        pages.extend(r)
        if len(r) < 100:
            break
        page += 1
    return pages

# ── 페이지 생성 ────────────────────────────────────────────
def upsert_page(base, pw, title, slug, content):
    code, r, _ = api("GET", f"{base}/pages", pw,
                      params={"slug": slug, "per_page":1})
    if isinstance(r, list) and r:
        return  # 이미 있음
    code, _, _ = api("POST", f"{base}/pages", pw,
                      {"title":title,"slug":slug,
                       "content":content,"status":"publish"})
    print(f"    {'✅' if code in(200,201) else '⚠️'} 페이지: {title} ({code})")

# ── 페이지 삭제 ────────────────────────────────────────────
def delete_page(base, pw, page_id):
    api("DELETE", f"{base}/pages/{page_id}", pw, params={"force": True})

# ── 포스트 카테고리 재배분 ─────────────────────────────────
def reassign_posts(base, pw, id1, id2, id3, kws2, kws3):
    """
    kws2 → cat2(id2), kws3 → cat3(id3), 나머지 → cat1(id1)
    """
    page = 1; moved = 0
    while True:
        code, posts, _ = api("GET", f"{base}/posts", pw,
                              params={"per_page":50,"page":page,
                                      "status":"publish","_fields":"id,title,categories"})
        if code != 200 or not isinstance(posts, list) or not posts:
            break
        for post in posts:
            title_lower = (post.get("title",{}).get("rendered","") or "").lower()
            current_cats = post.get("categories", [])

            # 이미 황금 카테고리에 정확히 배분돼 있으면 스킵
            if len(current_cats) == 1 and current_cats[0] in [id1,id2,id3]:
                continue

            target = id1  # 기본: 첫번째 황금카테고리
            for kw in kws3:
                if kw.lower() in title_lower:
                    target = id3; break
            if target == id1:
                for kw in kws2:
                    if kw.lower() in title_lower:
                        target = id2; break

            api("POST", f"{base}/posts/{post['id']}", pw,
                {"categories": [target]})
            moved += 1

        if len(posts) < 50:
            break
        page += 1
    if moved:
        print(f"    📝 포스트 {moved}개 재배분 완료")

# ── 색인 허용 ──────────────────────────────────────────────
def allow_indexing(base, pw):
    code, _, _ = api("POST", f"{base}/settings", pw, {"blog_public": True})
    print(f"    {'✅' if code<300 else '⚠️'} 색인 허용 (HTTP {code})")

# ── 사이트명 설정 ──────────────────────────────────────────
def set_site_title(base, pw, title):
    api("POST", f"{base}/settings", pw, {"title": title})

# ── 메뉴 정리 ──────────────────────────────────────────────
def update_menu(site_url, pw, keep_ids):
    code, menus, _ = api("GET", f"{site_url}/wp-json/wp/v2/menus", pw)
    if not isinstance(menus, list) or not menus:
        return
    menu_id = menus[0]["id"]
    code, items, _ = api("GET", f"{site_url}/wp-json/wp/v2/menu-items", pw,
                          params={"menu": menu_id, "per_page":100})
    if isinstance(items, list):
        for item in items:
            if (item.get("type") == "taxonomy"
                    and item.get("object") == "category"
                    and item.get("object_id") not in keep_ids):
                api("DELETE", f"{site_url}/wp-json/wp/v2/menu-items/{item['id']}",
                    pw, params={"force":True})
    for cid in keep_ids:
        if cid:
            api("POST", f"{site_url}/wp-json/wp/v2/menu-items", pw, {
                "menu_id": menu_id,
                "object_id": cid,
                "object": "category",
                "type": "taxonomy",
                "status": "publish"
            })
    print("    ✅ 메뉴 정리 완료")

# ════════════════════════════════════════════════════════════
# 메인 실행
# ════════════════════════════════════════════════════════════
def slug_of(name):
    s = name.lower()
    s = re.sub(r'[&]', 'and', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9가-힣\-]', '', s)
    return s.strip('-')

def run():
    results = []   # 색인 현황 수집용
    total = len(SITES); ok = 0; skipped = 0

    print("=" * 60)
    print("🚀 27개 사이트 완전 정리 시작")
    print("   [1] 카테고리 3개로 통합  [2] 포스트 자동 재배분")
    print("   [3] 필수 4페이지만 유지  [4] 색인 차단 해제")
    print("=" * 60)

    for i, row in enumerate(SITES, 1):
        (url, env_key, lang, site_title,
         c1, c2, c3,
         kws2, kws3,
         fix_idx) = row

        pw   = os.getenv(env_key, "")
        base = f"{url}/wp-json/wp/v2"
        print(f"\n[{i}/{total}] {url}")

        if not pw:
            print(f"  ⚠️ 비밀번호 없음 ({env_key}) — 스킵")
            results.append({"url":url,"status":"skip","posts":0,"cats":0,"pages":0})
            skipped += 1; continue

        # 접속 확인 + 포스트 수 파악
        code, _, headers = api("GET", f"{base}/posts", pw,
                                params={"per_page":1,"status":"publish"})
        if code == 0 or code >= 500:
            print(f"  ❌ 접속 불가 (HTTP {code})")
            results.append({"url":url,"status":"error","posts":0,"cats":0,"pages":0})
            skipped += 1; continue
        total_posts = int(headers.get("X-WP-Total", 0))
        print(f"  접속 OK | 포스트 {total_posts}건")

        # ── [1] 색인 허용 ──────────────────────────────────
        if fix_idx:
            print("  🔓 색인 차단 해제...")
            allow_indexing(base, pw)

        # ── [2] 황금 카테고리 3개 생성 ─────────────────────
        print(f"  📁 황금 카테고리 생성: {c1} / {c2} / {c3}")
        id1 = get_or_create_cat(base, pw, c1, slug_of(c1))
        id2 = get_or_create_cat(base, pw, c2, slug_of(c2))
        id3 = get_or_create_cat(base, pw, c3, slug_of(c3))
        keep_ids = [x for x in [id1,id2,id3] if x]

        # ── [3] 불필요 카테고리 삭제 (황금 3개 + ID=1 제외) ─
        print("  🗑️ 불필요 카테고리 삭제...")
        all_cats = get_all_cats(base, pw)
        deleted = 0
        for cat in all_cats:
            cid = cat.get("id")
            if cid in keep_ids or cid == 1:
                continue
            if delete_cat(base, pw, cid):
                deleted += 1
        print(f"    {deleted}개 카테고리 삭제")

        # ── [4] 포스트 황금 카테고리로 재배분 ──────────────
        if keep_ids and total_posts > 0:
            print("  📝 포스트 카테고리 재배분...")
            reassign_posts(base, pw, id1, id2, id3, kws2, kws3)

        # ── [5] 불필요 페이지 삭제 + 필수 4페이지 유지 ─────
        print("  📄 페이지 정리 (필수 4개만 유지)...")
        all_pages = get_all_pages(base, pw)
        page_deleted = 0; keep_count = 0
        for pg in all_pages:
            pg_slug = pg.get("slug","")
            # 필수 slug 계열은 유지
            is_keep = any(
                pg_slug == s or pg_slug.startswith(s)
                for s in KEEP_PAGE_SLUGS
            )
            if is_keep:
                keep_count += 1
            else:
                delete_page(base, pw, pg["id"])
                page_deleted += 1
        print(f"    페이지 {page_deleted}개 삭제 / {keep_count}개 유지")

        # 필수 4페이지 없으면 생성
        print("  📄 필수 4페이지 생성...")
        for ptitle, pslug, pcontent in required_pages(lang):
            upsert_page(base, pw, ptitle, pslug, pcontent)

        # ── [6] 사이트명 정상화 ─────────────────────────────
        print(f"  🏷️ 사이트명: {site_title}")
        set_site_title(base, pw, site_title)

        # ── [7] 메뉴 정리 ───────────────────────────────────
        print("  🗂️ 메뉴 정리...")
        update_menu(url, pw, keep_ids)

        # 최종 카테고리 수 확인
        final_cats = get_all_cats(base, pw)
        real_cats = [c for c in final_cats if c.get("id") != 1]

        results.append({
            "url": url, "status": "ok",
            "posts": total_posts,
            "cats": len(real_cats),
            "pages": keep_count + 4,
            "c1": c1, "c2": c2, "c3": c3,
        })

        print(f"  ✅ 완료 | 카테고리 {len(real_cats)}개 | 포스트 {total_posts}건")
        ok += 1
        time.sleep(2)

    # ── 최종 리포트 출력 ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("📊 27개 사이트 색인 발행 현황 리포트")
    print("=" * 60)
    print(f"{'순위':<4} {'도메인':<32} {'포스트':>6} {'카테':>4} {'상태'}")
    print("-" * 60)

    # 포스트 수 기준 내림차순
    results_sorted = sorted(results, key=lambda x: x.get("posts",0), reverse=True)
    for idx, r in enumerate(results_sorted, 1):
        status_icon = "✅" if r["status"]=="ok" else "⚠️" if r["status"]=="skip" else "❌"
        domain = r["url"].replace("https://","")
        posts  = r.get("posts",0)
        cats   = r.get("cats",0)
        bar    = "█" * min(posts//30, 15)
        print(f"  {idx:<3} {domain:<32} {posts:>6}건  {cats}개  {status_icon} {bar}")

    print("-" * 60)
    print(f"✅ 성공: {ok}개  |  ⚠️ 스킵: {skipped}개  |  총: {total}개")
    print()
    print("📌 다음 단계:")
    print("  1. Google Search Console → 각 사이트 sitemap 제출")
    print("  2. AdSense → 각 사이트 재심사 요청")
    print("  3. Actions → autopost → step=post 글 발행 시작")

if __name__ == "__main__":
    run()
