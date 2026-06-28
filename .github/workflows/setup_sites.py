#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_sites.py  —  27개 사이트 구조 자동 설정
위치: .github/workflows/setup_sites.py
실행: GitHub Actions [site-setup] job 에서 자동 호출

수행 작업:
  1. robots/noindex 차단 해제  (ksa-korea·kworld365·krealestate365)
  2. 황금 카테고리 3개 생성
  3. 필수 4페이지 생성         (Privacy·Disclaimer·Contact·About)
  4. 메뉴에 카테고리 등록
"""

import os, time, requests

WP_USER = "huh0303@gmail.com"

def api(method, url, pw, data=None):
    try:
        r = requests.request(
            method, url,
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json=data,
            headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"},
            timeout=18, verify=True
        )
        return r.status_code, (r.json() if r.text.strip() else {})
    except Exception as e:
        return 0, {"error": str(e)[:80]}

def get_or_create_cat(base, pw, name, slug, desc):
    _, cats = api("GET", f"{base}/categories?slug={requests.utils.quote(slug)}&per_page=1", pw)
    if isinstance(cats, list) and cats:
        print(f"    카테고리 존재: {name}")
        return cats[0]["id"]
    code, r = api("POST", f"{base}/categories", pw, {"name":name,"slug":slug,"description":desc})
    if code in (200,201) and r.get("id"):
        print(f"    ✅ 카테고리 생성: {name}")
        return r["id"]
    # slug 충돌 → 이름 검색으로 재조회
    _, cats2 = api("GET", f"{base}/categories?search={requests.utils.quote(name)}&per_page=10", pw)
    if isinstance(cats2, list):
        for c in cats2:
            if c.get("name","").lower().strip() == name.lower().strip():
                print(f"    카테고리 재확인: {name}")
                return c["id"]
    print(f"    ⚠️ 카테고리 실패: {name} (HTTP {code})")
    return None

def upsert_page(base, pw, title, slug, content):
    _, pages = api("GET", f"{base}/pages?slug={requests.utils.quote(slug)}&per_page=1", pw)
    if isinstance(pages, list) and pages:
        print(f"    페이지 존재: {title}")
        return
    code, r = api("POST", f"{base}/pages", pw,
                  {"title":title,"slug":slug,"content":content,"status":"publish"})
    print(f"    {'✅' if code in(200,201) else '⚠️'} 페이지: {title} ({code})")

def allow_indexing(base, pw):
    code, _ = api("POST", f"{base}/settings", pw, {"blog_public": True})
    print(f"    {'✅' if code<300 else '⚠️'} 색인 허용 설정 ({code})")

def add_to_menu(site_url, pw, cat_ids):
    _, menus = api("GET", f"{site_url}/wp-json/wp/v2/menus", pw)
    if not isinstance(menus, list) or not menus:
        print("    ℹ️ 메뉴 REST API 미지원 → WP 관리자에서 수동 추가")
        return
    for menu in menus[:1]:   # 첫 번째 메뉴에만 추가
        for cid in cat_ids:
            if cid:
                api("POST", f"{site_url}/wp-json/wp/v2/menu-items", pw, {
                    "menu_id": menu["id"], "object_id": cid,
                    "object": "category", "type": "taxonomy", "status": "publish"
                })
    print("    ✅ 메뉴 업데이트 완료")

# ── 필수 4페이지 내용 ──────────────────────────────────────
def pages(lang):
    if lang == "ko":
        return [
            ("개인정보처리방침","privacy-policy",
             "<h2>개인정보처리방침</h2>"
             "<p>본 사이트는 이용자의 개인정보를 소중히 여기며 관련 법령에 따라 보호합니다.</p>"
             "<ul><li>수집 항목: 이메일(문의 시), 방문 기록(분석 도구)</li>"
             "<li>이용 목적: 서비스 제공 및 통계 분석</li>"
             "<li>보유 기간: 이용 종료 후 즉시 파기</li></ul>"
             "<p>문의: huh0303@gmail.com</p>"),
            ("면책공고","disclaimer",
             "<h2>면책공고</h2>"
             "<p>본 사이트의 정보는 참고 목적으로만 제공됩니다. "
             "정보의 정확성을 보장하지 않으며 전문적 조언이 필요한 경우 관련 전문가와 상담하시기 바랍니다.</p>"),
            ("문의하기","contact",
             "<h2>문의하기</h2>"
             "<p>이메일: huh0303@gmail.com</p>"
             "<p>응답 시간: 영업일 기준 1~2일 이내</p>"),
            ("사이트 소개","about",
             "<h2>사이트 소개</h2>"
             "<p>한국에 관심 있는 분들을 위한 전문 정보 블로그입니다. "
             "정확하고 유용한 정보를 꾸준히 제공합니다.</p>"
             "<p>문의: huh0303@gmail.com</p>"),
        ]
    return [
        ("Privacy Policy","privacy-policy",
         "<h2>Privacy Policy</h2>"
         "<p>We are committed to protecting your privacy in compliance with applicable laws.</p>"
         "<ul><li>Information collected: Email (contact form), visit logs (analytics)</li>"
         "<li>Purpose: Service delivery and improvement</li>"
         "<li>Retention: Deleted upon service termination</li></ul>"
         "<p>Contact: huh0303@gmail.com</p>"),
        ("Disclaimer","disclaimer",
         "<h2>Disclaimer</h2>"
         "<p>All content on this site is for educational and informational purposes only. "
         "We make no warranties about accuracy or completeness. "
         "Please consult a qualified professional for specific advice.</p>"),
        ("Contact Us","contact",
         "<h2>Contact Us</h2>"
         "<p>Email: huh0303@gmail.com</p>"
         "<p>Response time: Within 1-2 business days</p>"),
        ("About Us","about",
         "<h2>About Us</h2>"
         "<p>This is a professional information blog about Korea. "
         "We provide accurate and useful content on a regular basis.</p>"
         "<p>Contact: huh0303@gmail.com</p>"),
    ]

# ── 27개 사이트 설정 테이블 ─────────────────────────────────
# (url, env_key, lang,
#  cat1, cat2, cat3,
#  desc1, desc2, desc3,
#  fix_indexing)
SITES = [
    # ── 건강 ─────────────────────────────────────────────────
    ("https://k-health365.com","KHEALTH365COM","ko",
     "건강의학정보","건강기능식품정보","질환별관리법",
     "질환정보 의학상식 건강뉴스","영양제 건강기능식품 보충제","질환관리법 생활습관 예방의학",
     False),
    ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM","en",
     "Surgery","Dental","Dermatology",
     "Plastic surgery and medical procedures Korea","Dental treatment and implants Korea","Dermatology aesthetics and skin Korea",
     False),
    # ── 투자·금융 ─────────────────────────────────────────────
    ("https://koreainvest365.com","KOREAINVEST365COM","en",
     "Stocks","Real Estate","Funds",
     "Korean stock market investing guide","Real estate investment Korea","ETF and fund investing Korea",
     False),
    ("https://ki-korea.com","KIKOREACOM","ko",
     "주식","부동산","절세",
     "한국 주식 ETF 투자 가이드","부동산 청약 분양 투자","절세 연금 세금 전략",
     False),
    ("https://koreainsurance365.com","KOREAINSURANCE365COM","en",
     "Health Insurance","Life Insurance","Auto Insurance",
     "Korean health insurance guide for foreigners","Life and accident insurance Korea","Auto and driver insurance Korea",
     False),
    ("https://kfinance365.com","KFINANCE365COM","en",
     "Banking","Investing","Taxes",
     "Korean banking and savings guide","Investment tips and strategies Korea","Tax guide for foreigners in Korea",
     False),
    ("https://koreataxnlaw.com","KOREATAXNLAWCOM","en",
     "Taxes","Business","Visas",
     "Korean tax guide for foreigners","Business setup and company registration Korea","Visa and immigration law Korea",
     False),
    ("https://koreacrypto365.com","KOREACRYPTO365COM","en",
     "Bitcoin","Exchanges","Regulation",
     "Bitcoin and Ethereum guide Korea","Korean crypto exchanges Upbit Bithumb","Crypto regulation and tax law Korea",
     False),
    ("https://krealestate365.com","KREALESTATE365COM","ko",
     "아파트","투자","세금",
     "아파트 청약 분양 시세 정보","부동산 투자 전략 분석","부동산 세금 법률 정책",
     True),    # robots 차단 해제
    # ── 테크·뷰티·K-pop ──────────────────────────────────────
    ("https://ktech365.com","KTECH365COM","en",
     "AI","Startups","Semiconductors",
     "AI and machine learning trends Korea","Korean startup ecosystem and venture","Semiconductor industry and chip Korea",
     False),
    ("https://kskin365.com","KSKIN365COM","en",
     "Skincare","Ingredients","Routines",
     "Korean skincare products and honest reviews","K-beauty ingredients science guide","Korean skincare routines step by step",
     False),
    ("https://oliveyoungkorea.com","OLIVEYOUNGKOREACOM","en",
     "Skincare","Makeup","Haircare",
     "Olive Young skincare honest reviews","K-beauty makeup products reviews","Korean haircare products guide",
     False),
    ("https://kworld365.com","KWORLD365COM","en",
     "Artists","Music","Tours",
     "K-pop artists profiles and news","K-pop albums and music releases","K-pop concerts and world tours",
     True),    # robots 차단 해제
    # ── 여행·비자·결혼 ────────────────────────────────────────
    ("https://k-trip365.com","KTRIP365COM","en",
     "Travel Guides","Food","Hotels",
     "Korea travel destination guides and tips","Korean food restaurants and street food","Hotels and accommodation reviews Korea",
     False),
    ("https://k-visa365.com","KVISA365COM","en",
     "Work Visa","Student Visa","Long-term Visa",
     "E-7 skilled worker visa Korea guide","D-2 student visa application Korea","F-2 F-5 long-term residence Korea",
     False),
    ("https://koreawedding365.com","KOREAWEDDING365COM","en",
     "Planning","Venues","Legal",
     "Korean wedding planning complete guide","Wedding venues and halls in Korea","Marriage registration and legal process Korea",
     False),
    # ── 유학·교육 ─────────────────────────────────────────────
    ("https://kstudy365.com","KSTUDY365COM","en",
     "Study Korea","Scholarships","Student Life",
     "Study in Korea university admission guide","Scholarships and TOPIK exam guide","Student visa campus life Korea",
     False),
    ("https://studyinkorea365.com","STUDYINKOREA365COM","en",
     "Admissions","Scholarships","Campus Life",
     "Korean university admission process guide","GKS government scholarship guide","International student life campus Korea",
     False),
    ("https://kieca-korea.org","KIECAKOREAORG","en",
     "Language","Culture","Careers",
     "Korean language learning guide for beginners","Korean culture and exchange programs","Study abroad and career in Korea",
     False),
    ("https://ksa-korea.org","KSAKOREAORG","ko",
     "입학정보","장학금","비자",
     "한국 대학 입학 전형 정보","정부초청 GKS 장학금 안내","유학생 비자 출입국 정보",
     True),    # noindex 해제
    ("https://sis-korea.com","SISKOREACOM","en",
     "Programs","Scholarships","TOPIK",
     "Academic degree programs and courses","Scholarship fees and funding guide","TOPIK Korean language proficiency test",
     False),
    # ── 취업 ──────────────────────────────────────────────────
    ("https://jobkorea365.com","JOBKOREA365COM","en",
     "Jobs","Salaries","Work Visa",
     "Jobs in Korea for foreigners complete guide","Salary and compensation guide Korea","Work visa E-7 application guide Korea",
     False),
    ("https://jobinkorea365.com","JOBINKOREA365COM","en",
     "Jobs","Interviews","Salaries",
     "Korea job search tips for foreigners","Job interview preparation Korea","Salary negotiation guide Korea",
     False),
    ("https://jobkoreaglobal.com","JOBKOREAGLOBALCOM","en",
     "Hiring","Salaries","Foreign Workers",
     "Global hiring and recruitment strategy Korea","Salary and benefits benchmarks Korea","Foreign worker EPS H-2 visa guide",
     False),
    # ── 문화·뉴스 ─────────────────────────────────────────────
    ("https://korea365.org","KOREA365ORG","en",
     "Korean Culture","Travel & Food","Living in Korea",
     "Korean culture traditions and history","Travel destinations and Korean food guide","Expat life and living tips in Korea",
     False),
    ("https://koreanews365.com","KOREANEWS365COM","ko",
     "경제","정치","사회",
     "한국 경제 금융 비즈니스 뉴스","한국 정치 외교 뉴스","한국 사회 문화 국제 IT 뉴스",
     False),
    ("https://theseouljournal.com","THESEOULJOURNALCOM","en",
     "Politics","Economy","Culture",
     "Korean politics diplomacy and global affairs","Korean economy business and markets","Korean culture K-pop arts and lifestyle",
     False),
]

def run():
    total = len(SITES); ok = 0; skipped = 0
    print("=" * 55)
    print(f"🚀 27개 사이트 구조 자동 설정 시작")
    print("=" * 55)

    for i, row in enumerate(SITES, 1):
        (url, env_key, lang,
         c1, c2, c3,
         d1, d2, d3,
         fix_idx) = row

        pw   = os.getenv(env_key, "")
        base = f"{url}/wp-json/wp/v2"
        print(f"\n[{i}/{total}] {url}")

        if not pw:
            print(f"  ⚠️ 비밀번호 없음 ({env_key}) — 스킵")
            skipped += 1; continue

        # 접속 확인
        code, _ = api("GET", f"{base}/posts?per_page=1", pw)
        if code == 0 or code >= 500:
            print(f"  ❌ 접속 불가 (HTTP {code})")
            skipped += 1; continue
        print(f"  접속 OK")

        # 1. 색인 허용 (noindex·robots 해제)
        if fix_idx:
            print("  🔓 색인 차단 해제...")
            allow_indexing(base, pw)

        # 2. 황금 카테고리 3개 생성
        print("  📁 카테고리 생성...")
        def slug(name):
            return name.lower().replace(" ","").replace("&","and").replace("·","")
        id1 = get_or_create_cat(base, pw, c1, slug(c1), d1)
        id2 = get_or_create_cat(base, pw, c2, slug(c2), d2)
        id3 = get_or_create_cat(base, pw, c3, slug(c3), d3)

        # 3. 필수 4페이지
        print("  📄 필수 4페이지 생성...")
        for ptitle, pslug, pcontent in pages(lang):
            upsert_page(base, pw, ptitle, pslug, pcontent)

        # 4. 메뉴 등록
        print("  🗂️ 메뉴 업데이트...")
        add_to_menu(url, pw, [id1, id2, id3])

        print(f"  ✅ 완료")
        ok += 1
        time.sleep(2)

    print("\n" + "=" * 55)
    print(f"✅ 성공: {ok}개  |  ⚠️ 스킵: {skipped}개  |  총: {total}개")
    print("=" * 55)

    if skipped > 0:
        print("\n⚠️  스킵된 사이트는 GitHub Secrets에 비밀번호가 없거나")
        print("    현재 접속 불가 상태입니다. Hostinger에서 확인해 주세요.")

if __name__ == "__main__":
    run()
