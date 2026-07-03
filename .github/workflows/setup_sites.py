#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_sites.py v4.0 — 27개 사이트 황금3+Etc 카테고리 완전 정리
★ 변경사항:
  - 카테고리 황금3 + Etc/기타 = 4개 고정
  - 11개 사이트 카테고리 신규 적용
  - 기존 글 재배분
  - 색인 요청 자동화 (IndexNow + Search Console ping)
"""

import os, time, re, requests
from datetime import datetime, timezone, timedelta

WP_USER = "huh0303@gmail.com"
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK","")
KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

KEEP_PAGE_SLUGS = {"privacy-policy","disclaimer","contact","about",
                   "contact-us","about-us","privacy","terms"}

def required_pages(lang):
    if lang == "ko":
        return [
            ("개인정보처리방침","privacy-policy",
             "<h2>개인정보처리방침</h2><p>본 사이트는 이용자의 개인정보를 소중히 여기며 관련 법령에 따라 보호합니다.</p>"
             "<ul><li>수집 항목: 이메일(문의 시), 방문 기록(분석 도구)</li>"
             "<li>이용 목적: 서비스 제공 및 통계 분석</li>"
             "<li>보유 기간: 이용 종료 후 즉시 파기</li></ul><p>문의: huh0303@gmail.com</p>"),
            ("면책공고","disclaimer",
             "<h2>면책공고</h2><p>본 사이트의 정보는 참고 목적으로만 제공됩니다.</p>"
             "<p>정보의 정확성을 보장하지 않으며 전문적 조언이 필요한 경우 관련 전문가와 상담하시기 바랍니다.</p>"),
            ("문의하기","contact",
             "<h2>문의하기</h2><p>이메일: huh0303@gmail.com</p><p>응답 시간: 영업일 기준 1~2일 이내</p>"),
            ("사이트 소개","about",
             "<h2>사이트 소개</h2><p>한국에 관심 있는 분들을 위한 전문 정보 블로그입니다.</p>"
             "<p>정확하고 유용한 정보를 꾸준히 제공합니다. 문의: huh0303@gmail.com</p>"),
        ]
    return [
        ("Privacy Policy","privacy-policy",
         "<h2>Privacy Policy</h2><p>We are committed to protecting your privacy in compliance with applicable laws.</p>"
         "<ul><li>Information collected: Email (contact form), visit logs (analytics)</li>"
         "<li>Purpose: Service delivery and improvement</li>"
         "<li>Retention: Deleted upon service termination</li></ul><p>Contact: huh0303@gmail.com</p>"),
        ("Disclaimer","disclaimer",
         "<h2>Disclaimer</h2><p>All content on this site is for educational and informational purposes only.</p>"
         "<p>We make no warranties about accuracy. Please consult a qualified professional for advice.</p>"),
        ("Contact Us","contact",
         "<h2>Contact Us</h2><p>Email: huh0303@gmail.com</p><p>Response time: Within 1-2 business days</p>"),
        ("About Us","about",
         "<h2>About Us</h2><p>This is a professional information blog about Korea.</p>"
         "<p>We provide accurate and useful content on a regular basis. Contact: huh0303@gmail.com</p>"),
    ]

def calc_adsense_grade(posts, cats, pages4, robots_ok, noindex_ok,
                       theme_ok, has_privacy, has_about, has_contact, has_disclaimer):
    score = 0
    if   posts >= 50:  score += 30
    elif posts >= 30:  score += 22
    elif posts >= 15:  score += 14
    elif posts >= 5:   score += 7
    if cats == 4:      score += 10
    elif cats == 3:    score += 8
    elif cats >= 1:    score += 5
    score += 5 if has_privacy    else 0
    score += 5 if has_about      else 0
    score += 5 if has_contact    else 0
    score += 5 if has_disclaimer else 0
    if robots_ok:   score += 10
    if noindex_ok:  score += 10
    if theme_ok:    score += 20
    if   score >= 85: grade = "A"
    elif score >= 70: grade = "B"
    elif score >= 50: grade = "C"
    elif score >= 30: grade = "D"
    else:             grade = "F"
    return score, grade

# ════════════════════════════════════════════════════════════
# ★ 27개 사이트 설정 v4.0 — 황금3 + Etc/기타
# ════════════════════════════════════════════════════════════
SITES = [
  # (url, env_key, lang, theme, site_title,
  #  c1, c2, c3,  kws2, kws3,  fix_idx, robots_ok, theme_ok)
  ("https://k-health365.com","KHEALTH365COM","ko","건강정보","K-Health365 건강정보",
   "건강의학정보","건강기능식품정보","질환별관리법",
   ["영양제","비타민","유산균","보충제","기능성","콜라겐","오메가","다이어트","체중","식품"],
   ["혈압","당뇨","혈당","암","피부","아토피","탈모","관절","허리","디스크","골다공증","수면","불면","우울","치료","예방","관리"],
   False, True, True),

  ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM","en","한국의료관광","Korea Medical Tour",
   "성형·피부과","정부지원혜택","비용·병원비",
   ["정부","지자체","서울시","부산","대구","인천","지원","혜택","보조","의료관광"],
   ["비용","가격","cost","price","fee","얼마","견적","할인","패키지","surgery cost"],
   False, True, True),

  ("https://koreainvest365.com","KOREAINVEST365COM","en","한국투자","Korea Invest 365",
   "Korea Stocks","Korea Funds & ETF","Crypto & Digital",
   ["ETF","fund","mutual","index","bond","dividend","yield","REIT","펀드"],
   ["crypto","bitcoin","ethereum","DeFi","NFT","blockchain","digital asset","upbit"],
   False, True, True),

  ("https://ki-korea.com","KIKOREACOM","en","한국투자(KO)","KI Korea 한국투자",
   "국내주식·ETF","부동산·청약","절세·연금",
   ["부동산","아파트","청약","분양","전세","리츠","토지","오피스텔"],
   ["절세","IRP","연금","비과세","공제","채권","금리","세금"],
   False, True, True),

  ("https://koreainsurance365.com","KOREAINSURANCE365COM","en","외국인보험","Korea Insurance 365",
   "외국인 건강보험","외국인 자동차보험","외국인 치과보험",
   ["car","auto","vehicle","driver","traffic","자동차","운전","교통사고"],
   ["dental","치과","implant","임플란트","tooth","teeth","scaling","orthodontics"],
   False, True, True),

  ("https://kfinance365.com","KFINANCE365COM","en","외국인금융","Korea Finance 365",
   "외국인 은행·송금","외국인 투자·주식","외국인 세금·환급",
   ["stock","invest","ETF","fund","KOSPI","trading","portfolio","dividend","주식"],
   ["tax","세금","refund","환급","VAT","income tax","deduction","신고","연말정산"],
   False, True, True),

  ("https://koreataxnlaw.com","KOREATAXNLAWCOM","en","외국인세금법률","Korea Tax & Law",
   "외국인 세금·신고","외국인 법인·창업","외국인 비자·체류",
   ["business","company","startup","corporation","법인","창업","registration","M&A"],
   ["visa","immigration","체류","residence","permit","비자","ARC","HiKorea","출입국"],
   False, True, True),

  ("https://koreacrypto365.com","KOREACRYPTO365COM","en","한국가상화폐","Korea Crypto 365",
   "업비트·거래소 가입","외국인 코인 투자법","한국 가상화폐 규제",
   ["foreign","외국인","invest","투자","buy","구매","how to","방법","guide","beginner"],
   ["regulation","규제","law","FSC","금융위","tax","세금","legal","policy","ban"],
   False, True, True),

  ("https://krealestate365.com","KREALESTATE365COM","en","외국인부동산","한국부동산 정석",
   "아파트 매매·전세·월세","상가·사업장 임대","외국인 대출·세금",
   ["상가","사무실","office","store","사업장","임대","월세","lease","commercial"],
   ["대출","loan","세금","tax","취득세","양도세","mortgage","은행","금리"],
   True, False, True),

  ("https://ktech365.com","KTECH365COM","en","한국테크AI","KTech365 Korea Tech",
   "AI","Startups","Semiconductors",
   ["startup","venture","unicorn","founder","funding"],
   ["semiconductor","chip","TSMC","fab","wafer","memory"],
   False, True, True),

  ("https://kskin365.com","KSKIN365COM","en","K-뷰티","KSkin365 K-Beauty",
   "Skincare","Ingredients","Routines",
   ["ingredient","niacinamide","hyaluronic","retinol","vitamin C","peptide"],
   ["routine","steps","morning","night","layering"],
   False, True, True),

  ("https://oliveyoungkorea.com","OLIVEYOUNGKOREACOM","en","K-뷰티리뷰","Olive Young Korea",
   "인기상품 TOP30","Skincare","Wellness",
   ["skincare","toner","serum","moisturizer","sunscreen","essence","ampoule","cream"],
   ["wellness","supplement","vitamin","probiotic","collagen","health","inner beauty"],
   False, True, True),

  ("https://kworld365.com","KWORLD365COM","en","K-Culture","KWorld365 K-Culture",
   "K-Pop & Artists","K-Culture & Learn Korean","Korean Life & Travel",
   ["learn korean","study korean","hangul","korean language","TOPIK","free korean"],
   ["travel","food","Seoul","Busan","Jeju","korean life","expat","kdrama"],
   False, True, True),

  ("https://k-trip365.com","KTRIP365COM","en","한국숙박여행","K-Trip365 Korea Stay & Travel",
   "Hotels & Stays","AirBnB & 민박","Travel Guides",
   ["airbnb","민박","guesthouse","pension","게스트하우스","여기어때","숙박"],
   ["guide","itinerary","travel","tour","trip","visit","attraction","sightseeing"],
   False, True, True),

  ("https://k-visa365.com","KVISA365COM","en","한국비자","K-Visa365 Korea Visa",
   "Work Visa","Student Visa","Long-term Visa",
   ["student","D-2","D-4","language school","university"],
   ["F-2","F-5","long-term","permanent","settlement"],
   False, True, True),

  ("https://koreawedding365.com","KOREAWEDDING365COM","en","한국국제결혼","Korea Wedding 365",
   "결혼·법적·비자","자녀국적·교육혜택","매칭·결혼비용",
   ["child","자녀","nationality","국적","education","교육","school","학교","benefit"],
   ["match","matchmaking","소개","맞선","비용","cost","price","wedding cost","결혼비용"],
   False, True, True),

  ("https://kstudy365.com","KSTUDY365COM","en","한국유학(플랫폼)","KStudy365 Study in Korea",
   "Study Korea","Scholarships","Student Life",
   ["scholarship","GKS","KGSP","funding","stipend","award"],
   ["student life","campus","dorm","visa","part-time"],
   False, True, True),

  ("https://studyinkorea365.com","STUDYINKOREA365COM","en","한국유학(국제)","Study in Korea 365",
   "Admissions","Scholarships","Campus Life",
   ["scholarship","GKS","government","KGSP","funding","financial aid"],
   ["campus","dormitory","housing","student life","clubs"],
   False, True, True),

  ("https://kieca-korea.org","KIECAKOREAORG","en","국제교육문화","KIECA Korea",
   "Language","Culture","Careers",
   ["culture","tradition","exchange","festival","history","art"],
   ["career","job","work","internship","employment"],
   False, True, True),

  ("https://ksa-korea.org","KSAKOREAORG","en","한국유학협회","KSA Korea 한국유학협회",
   "입학정보","장학금","비자",
   ["장학금","GKS","정부초청","지원금","면제"],
   ["비자","D-2","출입국","체류","연장"],
   True, True, False),

  ("https://sis-korea.com","SISKOREACOM","en","서울국제학교","SIS Korea",
   "Programs","Scholarships","TOPIK",
   ["scholarship","fee","funding","financial","tuition"],
   ["TOPIK","Korean test","language exam","proficiency","test prep"],
   False, True, True),

  ("https://jobkorea365.com","JOBKOREA365COM","en","한국취업(종합)","Job Korea 365",
   "Jobs","Salaries","Work Visa",
   ["salary","wage","income","pay","compensation","benefits"],
   ["visa","E-7","work permit","eligibility","sponsor"],
   False, True, True),

  ("https://jobinkorea365.com","JOBINKOREA365COM","en","한국취업","Jobs in Korea 365",
   "Jobs","Interviews","Salaries",
   ["interview","preparation","question","answer","tips","STAR"],
   ["salary","wage","negotiation","pay","compensation"],
   False, True, True),

  ("https://jobkoreaglobal.com","JOBKOREAGLOBALCOM","en","한국취업(글로벌)","Job Korea Global",
   "Hiring","Salaries","Foreign Workers",
   ["salary","compensation","benefits","pay scale","benchmark"],
   ["foreign worker","EPS","H-2","E-9","migrant","overseas"],
   False, True, True),

  ("https://korea365.org","KOREA365ORG","en","한국소식(종합)","Korea 365",
   "Korean Culture","Travel & Food","Living in Korea",
   ["travel","food","restaurant","cuisine","trip","tourism"],
   ["living","expat","foreigner","daily","tips","cost"],
   False, True, True),

  ("https://koreanews365.com","KOREANEWS365COM","ko","한국타임즈(뉴스)","한국타임즈",
   "경제","정치","사회",
   ["정치","대통령","국회","선거","외교","북한","여당","야당"],
   ["사회","범죄","복지","교육","문화","국제","IT","반도체"],
   False, True, True),

  ("https://theseouljournal.com","THESEOULJOURNALCOM","en","서울저널(영자)","The Seoul Journal",
   "Politics","Economy","Culture",
   ["economy","market","stock","trade","business","finance","GDP"],
   ["culture","K-pop","music","food","lifestyle","travel","expat"],
   False, True, True),
]

# ════════════════════════════════════════════════════════════
# API 유틸
# ════════════════════════════════════════════════════════════
def api(method, url, pw, data=None, params=None, timeout=20):
    try:
        r = requests.request(
            method, url,
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json=data, params=params,
            headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"},
            timeout=timeout, verify=True
        )
        try: body = r.json()
        except: body = {}
        return r.status_code, body, r.headers
    except Exception as e:
        return 0, {"error":str(e)[:60]}, {}

def get_all_cats(base, pw):
    cats=[]; page=1
    while True:
        code,r,_ = api("GET",f"{base}/categories",pw,params={"per_page":100,"page":page})
        if code!=200 or not isinstance(r,list) or not r: break
        cats.extend(r)
        if len(r)<100: break
        page+=1
    return cats

def get_or_create_cat(base, pw, name, slug):
    code,r,_ = api("GET",f"{base}/categories",pw,params={"slug":slug,"per_page":1})
    if isinstance(r,list) and r: return r[0]["id"]
    code,r,_ = api("POST",f"{base}/categories",pw,{"name":name,"slug":slug,"description":f"{name} category"})
    if code in(200,201) and r.get("id"):
        print(f"    ✅ 생성: {name}"); return r["id"]
    code,r,_ = api("GET",f"{base}/categories",pw,params={"search":name,"per_page":10})
    if isinstance(r,list):
        for c in r:
            if c.get("name","").strip().lower()==name.strip().lower(): return c["id"]
    return None

def delete_cat_force(base, pw, cat_id, fallback_id):
    page=1
    while True:
        code,posts,_ = api("GET",f"{base}/posts",pw,
                           params={"categories":cat_id,"per_page":50,"page":page,
                                   "_fields":"id","status":"any"},timeout=20)
        if code!=200 or not isinstance(posts,list) or not posts: break
        for post in posts:
            api("POST",f"{base}/posts/{post['id']}",pw,{"categories":[fallback_id]},timeout=10)
        if len(posts)<50: break
        page+=1
    code,_,_ = api("DELETE",f"{base}/categories/{cat_id}",pw,params={"force":True})
    return code in(200,201)

def reassign_posts_fast(base, pw, id1, id2, id3, id4, kws2, kws3):
    page=1; moved=0
    while True:
        code,posts,_ = api("GET",f"{base}/posts",pw,
                           params={"per_page":50,"page":page,"status":"publish",
                                   "_fields":"id,title,categories"},timeout=25)
        if code!=200 or not isinstance(posts,list) or not posts: break
        for post in posts:
            title_lower=(post.get("title",{}).get("rendered","") or "").lower()
            cur=post.get("categories",[])
            if len(cur)==1 and cur[0] in [id1,id2,id3,id4]: continue
            target=id1
            for kw in kws3:
                if kw.lower() in title_lower: target=id3; break
            if target==id1:
                for kw in kws2:
                    if kw.lower() in title_lower: target=id2; break
            api("POST",f"{base}/posts/{post['id']}",pw,{"categories":[target]},timeout=12)
            moved+=1
        if len(posts)<50: break
        page+=1
    if moved: print(f"    📝 {moved}개 포스트 재배분 완료")
    return moved

def get_all_pages(base, pw):
    pages=[]; page=1
    while True:
        code,r,_ = api("GET",f"{base}/pages",pw,params={"per_page":100,"page":page,"status":"any"})
        if code!=200 or not isinstance(r,list) or not r: break
        pages.extend(r)
        if len(r)<100: break
        page+=1
    return pages

def upsert_page(base, pw, title, slug, content):
    code,r,_ = api("GET",f"{base}/pages",pw,params={"slug":slug,"per_page":1})
    if isinstance(r,list) and r: return True
    code,_,_ = api("POST",f"{base}/pages",pw,
                   {"title":title,"slug":slug,"content":content,"status":"publish"})
    print(f"    {'✅' if code in(200,201) else '⚠️'} 페이지: {title}")
    return code in(200,201)

def check_pages(base, pw):
    result = {"privacy":False,"about":False,"contact":False,"disclaimer":False}
    for slug_set, key in [
        ({"privacy-policy","privacy"}, "privacy"),
        ({"about","about-us"}, "about"),
        ({"contact","contact-us"}, "contact"),
        ({"disclaimer"}, "disclaimer"),
    ]:
        for slug in slug_set:
            code,r,_ = api("GET",f"{base}/pages",pw,params={"slug":slug,"per_page":1})
            if isinstance(r,list) and r:
                result[key]=True; break
    return result

def check_noindex(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"}, verify=True)
        if "noindex" in r.text.lower() or "noindex" in r.headers.get("X-Robots-Tag","").lower():
            return False
        return True
    except:
        return None


# ════════════════════════════════════════════════════════════
# ★ v5.0 추가 함수들
# ════════════════════════════════════════════════════════════

def activate_gp_premium(site_url: str, pw: str) -> bool:
    """GeneratePress Premium 강제 활성화 + Elementor 완전 제거"""
    try:
        # 1. 현재 활성 테마 확인
        r = requests.get(f"{site_url}/wp-json/wp/v2/themes",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"status":"active"}, timeout=10)
        if r.status_code == 200:
            themes = r.json() if isinstance(r.json(), list) else list(r.json().values())
            for t in themes:
                slug = t.get("stylesheet","")
                if "generatepress" in slug.lower():
                    print(f"    ✅ GP 이미 활성화: {slug}")
                    break

        # 2. 설치된 테마 중 GP 찾아 활성화
        r2 = requests.get(f"{site_url}/wp-json/wp/v2/themes",
                         auth=requests.auth.HTTPBasicAuth(WP_USER, pw), timeout=10)
        if r2.status_code == 200:
            all_t = r2.json()
            themes_list = all_t if isinstance(all_t, list) else list(all_t.values())
            for t in themes_list:
                slug = t.get("stylesheet","") or t.get("template","")
                if "generatepress" in slug.lower():
                    act = requests.post(
                        f"{site_url}/wp-json/wp/v2/themes/{slug}",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        json={"status":"active"}, timeout=15)
                    if act.status_code in (200,201):
                        print(f"    ✅ GP Premium 활성화: {slug}")
                        return True

        # 3. WP Settings API로 테마 변경 시도
        r3 = requests.post(f"{site_url}/wp-json/wp/v2/settings",
                          auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                          json={"stylesheet":"generatepress"}, timeout=10)
        print(f"    ⚠️ GP REST 활성화 제한 → hPanel 수동 필요 ({r3.status_code})")
        return False
    except Exception as e:
        print(f"    ⚠️ GP 활성화 오류: {e}")
        return False


def remove_elementor_templates(site_url: str, pw: str):
    """Elementor 테마빌더 템플릿 전부 삭제"""
    removed = 0
    try:
        # elementor_library (테마빌더 템플릿) 조회
        for post_type in ["elementor_library", "wp_template", "wp_template_part"]:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/{post_type}",
                auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                params={"per_page":100, "status":"any"},
                timeout=10)
            if r.status_code == 200 and isinstance(r.json(), list):
                for item in r.json():
                    pid = item.get("id")
                    if pid:
                        dr = requests.delete(
                            f"{site_url}/wp-json/wp/v2/{post_type}/{pid}",
                            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                            params={"force":True}, timeout=8)
                        if dr.status_code in (200,201):
                            removed += 1
        if removed:
            print(f"    🗑️ Elementor 템플릿 {removed}개 삭제")
        else:
            print(f"    ✅ Elementor 템플릿 없음")
    except Exception as e:
        print(f"    ⚠️ Elementor 삭제 오류: {e}")
    return removed


def set_homepage_to_latest_posts(site_url: str, pw: str):
    """홈페이지를 최신글(블로그형)으로 강제 설정"""
    try:
        r = requests.post(
            f"{site_url}/wp-json/wp/v2/settings",
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json={"show_on_front":"posts", "page_on_front":0, "page_for_posts":0},
            timeout=10)
        if r.status_code in (200,201):
            print(f"    ✅ 홈페이지 → 최신글 설정 완료")
        else:
            print(f"    ⚠️ 홈페이지 설정 ({r.status_code})")
    except Exception as e:
        print(f"    ⚠️ 홈페이지 설정 오류: {e}")


def inject_menu_css(site_url: str, pw: str):
    """
    메뉴 2줄 통일 CSS:
    1줄 (작게, 어두운 배경, 우측정렬): Privacy Policy | Disclaimer | Contact Us | About Us
    2줄 (굵게, 파란 배경, 중앙): 황금 카테고리 4개
    Footer: 카테고리 4개만
    """
    css = """
/* ★ TOP BAR: 필수 4페이지 (작게, 어두운배경, 우측정렬) */
.top-bar, .site-top-bar {
    background: #1e2433 !important;
    padding: 4px 0 !important;
    font-size: 11px !important;
}
.top-bar .inside-top-bar,
.site-top-bar .inside {
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
    gap: 16px !important;
}
.top-bar a, .site-top-bar a {
    color: #aab4c8 !important;
    font-size: 11px !important;
    text-decoration: none !important;
    letter-spacing: 0.3px !important;
}
.top-bar a:hover, .site-top-bar a:hover {
    color: #ffffff !important;
}

/* ★ MAIN NAV: 황금 카테고리 4개 (굵게, 파란배경, 중앙) */
.main-navigation, .site-navigation, #site-navigation {
    background: #1a6fd4 !important;
    padding: 0 !important;
}
.main-navigation .menu,
.main-navigation ul,
.site-navigation ul {
    display: flex !important;
    justify-content: center !important;
    list-style: none !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
}
.main-navigation a,
.site-navigation a {
    color: #ffffff !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 12px 22px !important;
    display: block !important;
    text-decoration: none !important;
    letter-spacing: 0.3px !important;
    transition: background 0.2s !important;
}
.main-navigation a:hover,
.site-navigation a:hover,
.main-navigation .current-menu-item > a {
    background: #1558aa !important;
    color: #ffffff !important;
}

/* ★ FOOTER: 카테고리 4개만 */
.site-footer .menu, .footer-navigation ul,
.footer-menu ul, #footer-menu ul {
    display: flex !important;
    justify-content: center !important;
    flex-wrap: wrap !important;
    gap: 8px 24px !important;
    list-style: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
.site-footer a, .footer-navigation a,
.footer-menu a {
    color: #aab4c8 !important;
    font-size: 13px !important;
    text-decoration: none !important;
}
.site-footer a:hover, .footer-navigation a:hover {
    color: #ffffff !important;
}

/* ★ 이미지 대표이미지 잘 보이게 */
.post-thumbnail img,
.wp-post-image,
article img:first-of-type {
    width: 100% !important;
    height: auto !important;
    border-radius: 6px !important;
    display: block !important;
    margin-bottom: 16px !important;
}

/* ★ 사이트 헤더 여백 */
.site-header {
    background: #ffffff !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}
"""
    try:
        r = requests.post(
            f"{site_url}/wp-json/wp/v2/settings",
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json={"custom_css": css},
            timeout=10)
        if r.status_code in (200, 201):
            print(f"    ✅ 메뉴 CSS 삽입 완료")
            return True

        # WPCode로 추가 CSS 삽입
        base = f"{site_url}/wp-json/wp/v2"
        snippet_data = {
            "title": "Menu Layout CSS v2",
            "content": f"<style>{css}</style>",
            "code_type": "html",
            "location": "site_header",
            "status": "publish",
        }
        r2 = requests.get(f"{base}/wpcode-snippets",
                         auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                         params={"per_page": 50}, timeout=10)
        if r2.status_code == 200 and isinstance(r2.json(), list):
            for s in r2.json():
                t = s.get("title", {})
                if "Menu Layout CSS" in (t.get("rendered","") if isinstance(t,dict) else str(t)):
                    ur = requests.post(f"{base}/wpcode-snippets/{s['id']}",
                                      auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                      json=snippet_data, timeout=10)
                    if ur.status_code in (200,201):
                        print(f"    ✅ 메뉴 CSS WPCode 업데이트")
                        return True
        cr = requests.post(f"{base}/wpcode-snippets",
                          auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                          json=snippet_data, timeout=10)
        if cr.status_code in (200,201):
            print(f"    ✅ 메뉴 CSS WPCode 생성")
            return True
        print(f"    ⚠️ CSS 삽입 ({r.status_code})")
        return False
    except Exception as e:
        print(f"    ⚠️ CSS 오류: {e}")
        return False


def setup_dual_menu(site_url: str, pw: str, lang: str,
                    cat_ids: list, cat_names: list, page_ids_map: dict):
    """
    2줄 메뉴 강제 구성:
    Top Bar (어두운색): Privacy Policy | Disclaimer | Contact Us | About Us
    Main Nav (파란색): 카테고리1 | 카테고리2 | 카테고리3 | Etc
    """
    base = f"{site_url}/wp-json"
    
    try:
        # 기존 메뉴 전부 조회
        r = requests.get(f"{base}/wp/v2/menus",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw), timeout=10)
        existing = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
        
        # 기존 메뉴 아이템 전부 삭제
        for menu in existing:
            mid = menu.get("id") or menu.get("term_id")
            if not mid: continue
            ir = requests.get(f"{base}/wp/v2/menu-items",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             params={"menus": mid, "per_page": 100}, timeout=10)
            if ir.status_code == 200:
                for item in ir.json():
                    requests.delete(f"{base}/wp/v2/menu-items/{item['id']}",
                                   auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                   params={"force": True}, timeout=8)

        # ── Primary Menu 생성 (카테고리) ──
        primary_id = None
        for m in existing:
            if "primary" in (m.get("slug","") or "").lower() or                "main" in (m.get("name","") or "").lower():
                primary_id = m.get("id") or m.get("term_id")
                break
        if not primary_id:
            cr = requests.post(f"{base}/wp/v2/menus",
                              auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              json={"name":"Primary Menu","slug":"primary-menu"}, timeout=10)
            if cr.status_code in (200,201):
                primary_id = cr.json().get("id")

        # ── Secondary Menu 생성 (페이지) ──
        secondary_id = None
        for m in existing:
            if "secondary" in (m.get("slug","") or "").lower() or                "top" in (m.get("name","") or "").lower():
                secondary_id = m.get("id") or m.get("term_id")
                break
        if not secondary_id:
            cr2 = requests.post(f"{base}/wp/v2/menus",
                               auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                               json={"name":"Secondary Menu","slug":"secondary-menu"}, timeout=10)
            if cr2.status_code in (200,201):
                secondary_id = cr2.json().get("id")

        # ── Footer Menu 생성 ──
        footer_id = None
        for m in existing:
            if "footer" in (m.get("slug","") or "").lower():
                footer_id = m.get("id") or m.get("term_id")
                break
        if not footer_id:
            cr3 = requests.post(f"{base}/wp/v2/menus",
                               auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                               json={"name":"Footer Menu","slug":"footer-menu"}, timeout=10)
            if cr3.status_code in (200,201):
                footer_id = cr3.json().get("id")

        # ── Primary Menu에 카테고리 4개 등록 ──
        cat_added = 0
        if primary_id:
            for order, (cid, cname) in enumerate(zip(cat_ids, cat_names), 1):
                if not cid or cid <= 0: continue
                r = requests.post(f"{base}/wp/v2/menu-items",
                                 auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                 json={"menus": primary_id, "object_id": cid,
                                       "object":"category","type":"taxonomy",
                                       "menu_order": order, "status":"publish"},
                                 timeout=10)
                if r.status_code in (200,201): cat_added += 1
            print(f"    ✅ 메인메뉴(카테고리) {cat_added}개 등록")

        # ── Secondary + Footer에 필수 4페이지 등록 ──
        page_order_list = [
            ("privacy-policy", "Privacy Policy" if lang=="en" else "개인정보처리방침"),
            ("disclaimer",     "Disclaimer"     if lang=="en" else "면책공고"),
            ("contact",        "Contact Us"     if lang=="en" else "문의하기"),
            ("about",          "About Us"       if lang=="en" else "사이트 소개"),
        ]
        base_api = f"{site_url}/wp-json/wp/v2"
        page_added = 0
        for order, (slug, label) in enumerate(page_order_list, 1):
            page_id = page_ids_map.get(slug)
            if not page_id:
                pr = requests.get(f"{base_api}/pages",
                                 auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                 params={"slug":slug,"per_page":1}, timeout=8)
                if pr.status_code==200 and pr.json():
                    page_id = pr.json()[0]["id"]
            if not page_id: continue

            # Secondary에만 페이지 등록 (Footer는 카테고리만)
            if secondary_id:
                r = requests.post(f"{base}/wp/v2/menu-items",
                                 auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                 json={"menus": secondary_id, "object_id": page_id,
                                       "object":"page","type":"post_type",
                                       "title": label, "menu_order": order,
                                       "status":"publish"},
                                 timeout=10)
            page_added += 1

        # ── Footer: 카테고리 4개만 ──
        if footer_id:
            for order2, (cid, cname) in enumerate(zip(cat_ids, cat_names), 1):
                if not cid or cid <= 0: continue
                requests.post(f"{base}/wp/v2/menu-items",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             json={"menus": footer_id, "object_id": cid,
                                   "object":"category","type":"taxonomy",
                                   "menu_order": order2, "status":"publish"},
                             timeout=10)

        print(f"    ✅ 보조메뉴/Footer(필수페이지) {page_added}개 등록")

        # 메뉴 위치 등록
        loc_payload = {}
        if primary_id:   loc_payload["primary"] = primary_id
        if secondary_id: loc_payload["secondary"] = secondary_id
        if footer_id:    loc_payload["footer"] = footer_id
        if loc_payload:
            requests.post(f"{base}/wp/v2/menu-locations",
                         auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                         json=loc_payload, timeout=10)

    except Exception as e:
        print(f"    ⚠️ 메뉴 구성 오류: {e}")


def set_site_language(site_url: str, pw: str, lang: str):
    """사이트 언어 강제 설정 (ko_KR 또는 en_US)"""
    locale = "ko_KR" if lang == "ko" else "en_US"
    try:
        r = requests.post(
            f"{site_url}/wp-json/wp/v2/settings",
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json={"language": locale, "WPLANG": locale},
            timeout=10)
        print(f"    {'✅' if r.status_code in (200,201) else '⚠️'} 언어 설정: {locale} ({r.status_code})")
    except Exception as e:
        print(f"    ⚠️ 언어 설정 오류: {e}")


def verify_post_seo(site_url: str, pw: str, limit: int = 10):
    """최근 글 SEO 기본 확인 (featured image + focus keyword)"""
    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            params={"per_page": limit, "status":"publish",
                    "_fields":"id,title,featured_media,meta"},
            timeout=12)
        if r.status_code != 200:
            return
        posts = r.json()
        no_img = 0
        no_kw = 0
        for p in posts:
            if not p.get("featured_media"):
                no_img += 1
            meta = p.get("meta", {})
            if not meta.get("rank_math_focus_keyword",""):
                no_kw += 1
        total = len(posts)
        print(f"    📊 최근{total}글 | 이미지없음:{no_img}건 | 키워드없음:{no_kw}건")
    except Exception as e:
        print(f"    ⚠️ SEO 확인 오류: {e}")



def fix_post_noindex_and_404(site_url: str, pw: str):
    """기존 글 noindex 제거 + 404 태그/카테고리 정리"""
    base = f"{site_url}/wp-json/wp/v2"
    fixed = 0
    
    try:
        # 1. 전체 글 noindex 제거 (Rank Math meta)
        page = 1
        while True:
            r = requests.get(f"{base}/posts",
                           auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                           params={"per_page":50, "page":page, "status":"publish",
                                   "_fields":"id,meta"},
                           timeout=15)
            if r.status_code != 200 or not r.json(): break
            posts = r.json()
            for post in posts:
                meta = post.get("meta", {})
                robots = meta.get("rank_math_robots", [])
                # noindex가 있으면 제거
                if isinstance(robots, list) and "noindex" in robots:
                    new_robots = [r for r in robots if r != "noindex"]
                    requests.post(
                        f"{base}/posts/{post['id']}",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        json={"meta": {"rank_math_robots": new_robots}},
                        timeout=10)
                    fixed += 1
                elif isinstance(robots, str) and "noindex" in robots:
                    requests.post(
                        f"{base}/posts/{post['id']}",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        json={"meta": {"rank_math_robots": []}},
                        timeout=10)
                    fixed += 1
            if len(posts) < 50: break
            page += 1
            
        if fixed:
            print(f"    ✅ noindex 제거: {fixed}개 글")
        else:
            print(f"    ✅ noindex 문제 없음")
            
        # 2. 사용하지 않는 태그 정리 (404 방지)
        r = requests.get(f"{base}/tags",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"per_page":100, "hide_empty":True},
                        timeout=10)
        if r.status_code == 200:
            tags = r.json()
            print(f"    📌 활성 태그: {len(tags)}개")
            
    except Exception as e:
        print(f"    ⚠️ 오류: {e}")


def audit_and_clean_posts(site_url: str, pw: str, lang: str, dry_run: bool = False):
    """
    ★ v2.0 엄격 기준 저품질 글 정리
    삭제 기준:
    1. 제목에 2020~2025 연도 포함
    2. 중복/유사 제목 (앞 20자 동일)
    3. 진부한 제목 패턴 (Complete Guide, Ultimate Guide, 총정리 등)
    4. 카테고리 주제 벗어난 글 (사이트 테마와 무관한 키워드)
    5. SEO 점수 낮은 글 (본문 너무 짧거나 이미지 없음)
    """
    import re as _re, html as _html
    base = f"{site_url}/wp-json/wp/v2"
    domain = site_url.replace("https://","")

    # ── 사이트별 허용 토픽 키워드 ──────────────────────────
    SITE_TOPICS = {
        "k-health365.com": ["건강","의학","질환","증상","치료","예방","영양","비타민","약","수면","통증","혈압","당뇨","암","피부","탈모","관절","다이어트","면역","보충제","한방"],
        "koreamedicaltour.com": ["medical","surgery","dental","dermatology","clinic","hospital","treatment","korea","plastic","skin","laser","botox","aesthetic","health","tour","cost","price"],
        "koreainvest365.com": ["invest","stock","ETF","fund","crypto","bitcoin","KOSPI","market","korea","dividend","portfolio","trading","asset","financial"],
        "ki-korea.com": ["주식","ETF","부동산","청약","절세","연금","투자","금융","코스피","펀드","채권","IRP","세금"],
        "koreainsurance365.com": ["insurance","건강보험","자동차보험","치과보험","foreigner","expat","coverage","policy","premium","health","auto","dental"],
        "kfinance365.com": ["finance","banking","tax","invest","송금","세금","환급","은행","외국인","foreigner","refund","VAT","income"],
        "koreataxnlaw.com": ["tax","법인","visa","세금","비자","창업","foreigner","law","legal","corporate","business","immigration"],
        "koreacrypto365.com": ["crypto","bitcoin","upbit","bithumb","exchange","거래소","blockchain","regulation","DeFi","NFT","coin","투자"],
        "krealestate365.com": ["부동산","아파트","전세","월세","매매","임대","대출","세금","상가","foreigner","real estate","property"],
        "ktech365.com": ["AI","tech","startup","semiconductor","chip","innovation","korea","technology","robot","digital","software"],
        "kskin365.com": ["skincare","skin","beauty","K-beauty","ingredient","routine","serum","toner","moisturizer","sunscreen","korean"],
        "oliveyoungkorea.com": ["olive young","skincare","beauty","K-beauty","product","wellness","supplement","makeup","review","korean"],
        "kworld365.com": ["K-pop","artist","music","concert","tour","idol","album","BTS","BLACKPINK","kpop","entertainment"],
        "k-trip365.com": ["hotel","travel","korea","airbnb","accommodation","stay","trip","tour","tourism","booking","숙박","여행"],
        "k-visa365.com": ["visa","immigration","permit","D-2","E-7","F-5","korea","foreigner","residence","work","student"],
        "koreawedding365.com": ["wedding","marriage","결혼","비자","국적","자녀","matchmaking","cost","legal","spouse"],
        "kstudy365.com": ["study","korea","university","scholarship","student","GKS","campus","TOPIK","admission","academic"],
        "studyinkorea365.com": ["study","korea","university","scholarship","campus","student","admission","international","academic"],
        "kieca-korea.org": ["language","culture","career","education","international","korean","exchange","program"],
        "ksa-korea.org": ["유학","입학","장학금","비자","한국","대학","외국인","scholarship","admission"],
        "sis-korea.com": ["program","scholarship","TOPIK","korea","international","student","career","language"],
        "jobkorea365.com": ["job","work","korea","salary","visa","employment","foreigner","career","E-7","hiring"],
        "jobinkorea365.com": ["job","korea","interview","salary","work","foreigner","employment","career","resume"],
        "jobkoreaglobal.com": ["hiring","recruitment","global","salary","foreign","worker","korea","career","international"],
        "korea365.org": ["korea","culture","travel","food","living","expat","lifestyle","tourist","korean","guide"],
        "koreanews365.com": ["경제","정치","사회","한국","뉴스","정책","시장","기업","국제","문화"],
        "theseouljournal.com": ["korea","politics","economy","culture","seoul","news","society","business","international"],
    }

    topic_keywords = SITE_TOPICS.get(domain, [])

    # ── 진부한 패턴 (삭제) ──────────────────────────────────
    CLICHE_PATTERNS = [
        r'complete guide to', r'ultimate guide', r'your complete guide',
        r'everything you need to know', r'a to z', r'a-to-z',
        r'총정리', r'완벽\s*가이드', r'모든\s*것', r'알아보자',
        r'top \d+ (?:reasons|tips|ways|things)',
        r'\d+ essential (?:tips|insights|reasons|things)',
        r'the essential guide', r'your essential guide',
        r'\*\*',  # markdown 별표
    ]

    # ── 연도 패턴 ────────────────────────────────────────────
    YEAR_PATTERNS = [r'202[0-5]', r'202[0-5]년']

    # 전체 글 수집
    all_posts = []
    page = 1
    while True:
        r = requests.get(f"{base}/posts",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"per_page":100,"page":page,"status":"publish",
                                "_fields":"id,title,date,slug,content,categories"},
                        timeout=20)
        if r.status_code != 200 or not isinstance(r.json(), list) or not r.json():
            break
        posts = r.json()
        all_posts.extend(posts)
        if len(posts) < 100: break
        page += 1

    print(f"    📋 전체 {len(all_posts)}건 엄격 분석 중...")

    to_delete = {}  # pid → (title, date, reason)
    title_seen = {}

    for post in all_posts:
        raw = post.get("title", {})
        title = raw.get("rendered","") if isinstance(raw, dict) else str(raw)
        title = _html.unescape(title)
        title = _re.sub(r'<[^>]+>', '', title).strip()
        pid = post.get("id")
        date = post.get("date","")[:10]

        # 본문 길이 확인
        raw_content = post.get("content", {})
        content_html = raw_content.get("rendered","") if isinstance(raw_content, dict) else ""
        plain_text = _re.sub('<[^>]+>', '', content_html).strip()
        content_len = len(plain_text.replace(' ','').replace(chr(10),''))

        title_lower = title.lower()

        # 1. 연도 포함
        for pat in YEAR_PATTERNS:
            if _re.search(pat, title, _re.IGNORECASE):
                to_delete[pid] = (title, date, "연도포함")
                break

        if pid in to_delete: continue

        # 2. 진부한 패턴
        for pat in CLICHE_PATTERNS:
            if _re.search(pat, title_lower, _re.IGNORECASE):
                to_delete[pid] = (title, date, "진부한패턴")
                break

        if pid in to_delete: continue

        # 3. 중복 제목 (앞 20자)
        key = _re.sub(r'\s+','', title[:20].lower())
        if key in title_seen:
            to_delete[pid] = (title, date, "중복제목")
        else:
            title_seen[key] = pid

        if pid in to_delete: continue

        # 4. 카테고리 주제 벗어남 (토픽 키워드 없음)
        if topic_keywords and content_len > 0:
            title_and_content = (title_lower + " " + plain_text[:500].lower())
            topic_match = any(kw.lower() in title_and_content for kw in topic_keywords)
            if not topic_match:
                to_delete[pid] = (title, date, "주제이탈")

        if pid in to_delete: continue

        # 5. 본문 너무 짧음 (1000자 미만 = 확실한 저품질)
        if content_len < 800:
            to_delete[pid] = (title, date, f"본문짧음({content_len}자)")

    delete_list = list(to_delete.items())
    print(f"    🗑️ 삭제 대상: {len(delete_list)}건")
    for pid, (title, date, reason) in delete_list[:15]:
        print(f"       [{reason}] {date} ID:{pid} {title[:55]}")
    if len(delete_list) > 15:
        print(f"       ... 외 {len(delete_list)-15}건")

    deleted = 0
    if not dry_run and delete_list:
        for pid, (title, date, reason) in delete_list:
            try:
                dr = requests.delete(
                    f"{base}/posts/{pid}",
                    auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                    params={"force": True},
                    timeout=15)
                if dr.status_code in (200, 201):
                    deleted += 1
            except Exception as e:
                pass
        print(f"    ✅ {deleted}건 삭제 완료 | 남은 글: {len(all_posts)-deleted}건")
    elif dry_run:
        print(f"    ℹ️ dry_run — 실제 삭제 안 함")

    return deleted




def cleanup_medicaltour(site_url: str, pw: str):
    """koreamedicaltour.com 전용:
    1. 한국어 글 전부 삭제
    2. 수술/주사기/메스 관련 이미지 포함 글 삭제
    """
    import re as _re
    base = f"{site_url}/wp-json/wp/v2"
    
    BLOCK_WORDS_KO = ["수술", "성형수술", "지방흡입", "주사기", "메스", "절개", "봉합",
                       "수술실", "마취", "시술", "보톡스주사", "필러주사"]
    BLOCK_WORDS_EN = ["surgery photo", "operating room", "scalpel", "incision",
                       "surgical procedure", "anesthesia", "needle injection"]
    
    deleted = 0
    page = 1
    while True:
        r = requests.get(f"{base}/posts",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"per_page": 50, "page": page, "status": "publish",
                                "_fields": "id,title,content,lang"},
                        timeout=20)
        if r.status_code != 200 or not isinstance(r.json(), list) or not r.json():
            break
        posts = r.json()
        
        for post in posts:
            raw = post.get("title", {})
            title = raw.get("rendered", "") if isinstance(raw, dict) else str(raw)
            title = _re.sub('<[^>]+>', '', title).strip()
            
            raw_c = post.get("content", {})
            body = raw_c.get("rendered", "") if isinstance(raw_c, dict) else ""
            plain = _re.sub('<[^>]+>', '', body).strip()
            
            pid = post.get("id")
            should_delete = False
            reason = ""
            
            # 1. 한국어 글 감지 (한글 비율 30% 이상)
            ko_chars = len(_re.findall(r'[가-힣]', plain[:500]))
            total_chars = len(plain[:500].replace(' ', ''))
            if total_chars > 0 and ko_chars / total_chars > 0.3:
                should_delete = True
                reason = "한국어글"
            
            # 2. 수술 관련 키워드
            if not should_delete:
                combined = (title + " " + plain[:300]).lower()
                for bw in BLOCK_WORDS_KO + BLOCK_WORDS_EN:
                    if bw.lower() in combined:
                        should_delete = True
                        reason = f"수술관련({bw})"
                        break
            
            if should_delete:
                dr = requests.delete(f"{base}/posts/{pid}",
                                    auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                    params={"force": True}, timeout=10)
                if dr.status_code in (200, 201):
                    deleted += 1
                    print(f"    🗑️ [{reason}] {title[:50]}")
        
        if len(posts) < 50: break
        page += 1
    
    print(f"    ✅ koreamedicaltour 정리 완료: {deleted}건 삭제")
    return deleted


def fix_ads_txt(site_url: str, pw: str, publisher_id: str = "pub-3456727916386941"):
    """ads.txt WPCode PHP snippet으로 자동 삽입"""
    ads_line = "google.com, " + publisher_id + ", DIRECT, f08c47fec0942fa0"
    
    php_code = (
        "<?php\n"
        "if (isset($_SERVER[\"REQUEST_URI\"]) && $_SERVER[\"REQUEST_URI\"] === \"/ads.txt\") {\n"
        "    header(\"Content-Type: text/plain\");\n"
        "    echo \"" + ads_line + "\";\n"
        "    exit;\n"
        "}\n"
        "?>"
    )
    
    try:
        base = f"{site_url}/wp-json/wp/v2"
        
        # 기존 ads.txt 스니펫 확인
        r = requests.get(f"{base}/wpcode-snippets",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"per_page": 50}, timeout=10)
        
        snippet_data = {
            "title": "ads.txt AdSense",
            "code_type": "php",
            "location": "everywhere",
            "status": "publish",
            "content": php_code,
        }
        
        if r.status_code == 200 and isinstance(r.json(), list):
            for s in r.json():
                title_raw = s.get("title", {})
                title_str = title_raw.get("rendered","") if isinstance(title_raw, dict) else str(title_raw)
                if "ads.txt" in title_str.lower():
                    ur = requests.post(
                        f"{base}/wpcode-snippets/{s['id']}",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        json=snippet_data, timeout=10)
                    if ur.status_code in (200,201):
                        print(f"    ✅ ads.txt 스니펫 업데이트")
                        return True
        
        # 새로 생성
        cr = requests.post(f"{base}/wpcode-snippets",
                          auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                          json=snippet_data, timeout=10)
        if cr.status_code in (200,201):
            print(f"    ✅ ads.txt 스니펫 생성")
            return True
        
        print(f"    ⚠️ ads.txt 삽입 실패 ({cr.status_code})")
        return False
        
    except Exception as e:
        print(f"    ⚠️ ads.txt 오류: {e}")
        return False

def ping_search_engines(site_url: str):
    """Google + Naver + Bing Sitemap ping"""
    sitemap = f"{site_url}/sitemap_index.xml"
    pings = [
        f"https://www.google.com/ping?sitemap={requests.utils.quote(sitemap)}",
        f"https://www.bing.com/ping?sitemap={requests.utils.quote(sitemap)}",
    ]
    for ping_url in pings:
        try:
            r = requests.get(ping_url, timeout=8)
            engine = "Google" if "google" in ping_url else "Bing"
            print(f"    🔍 {engine} ping: HTTP {r.status_code}")
        except Exception as e:
            print(f"    ⚠️ ping 실패: {e}")


def install_github_ip_whitelist(site_url: str, pw: str):
    """WPCode Lite로 GitHub Actions IP 허용 코드 삽입"""
    base = f"{site_url}/wp-json/wp/v2"
    
    php_code = """<?php
// GitHub Actions IP Whitelist for WordPress REST API
add_filter('rest_authentication_errors', function($result) {
    $allowed_ranges = ['4.148.', '20.1.', '20.200.', '40.74.', '192.30.', '185.199.', '140.82.'];
    $ip = $_SERVER['REMOTE_ADDR'] ?? $_SERVER['HTTP_X_FORWARDED_FOR'] ?? '';
    $ip = trim(explode(',', $ip)[0]);
    foreach ($allowed_ranges as $range) {
        if (strpos($ip, $range) === 0) return true;
    }
    return $result;
}, 10, 1);

// Also allow REST API access
add_filter('rest_enabled', '__return_true');
add_filter('rest_jsonp_enabled', '__return_true');
"""
    
    # WPCode REST API로 스니펫 삽입
    try:
        # 기존 스니펫 확인
        r = requests.get(f"{base}/wpcode-snippets",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"per_page": 20}, timeout=10)
        
        snippet_data = {
            "title": "GitHub Actions IP Whitelist",
            "content": php_code,
            "code_type": "php",
            "status": "publish",
            "location": "everywhere",
        }
        
        if r.status_code == 200 and r.json():
            # 기존 스니펫 업데이트
            for s in r.json():
                if "GitHub Actions" in s.get("title", {}).get("rendered", ""):
                    ur = requests.post(
                        f"{base}/wpcode-snippets/{s['id']}",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        json=snippet_data, timeout=10)
                    if ur.status_code in (200,201):
                        print(f"    ✅ IP 허용 코드 업데이트")
                        return True
        
        # 새로 생성
        cr = requests.post(f"{base}/wpcode-snippets",
                          auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                          json=snippet_data, timeout=10)
        if cr.status_code in (200,201):
            print(f"    ✅ IP 허용 코드 삽입 완료")
            return True
            
        # WPCode API 없으면 wp_options에 직접
        print(f"    ⚠️ WPCode API 없음 → wp_options 방식 시도")
        
        # functions.php에 코드 추가 (wp-json/wp/v2/settings 경유)
        r2 = requests.post(f"{site_url}/wp-json/wp/v2/settings",
                          auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                          json={"wpcode_auto_insert": php_code},
                          timeout=10)
        return False
        
    except Exception as e:
        print(f"    ⚠️ IP 허용 코드 삽입 실패: {e}")
        return False


def setup_rank_math_indexing(site_url: str, pw: str):
    """Rank Math Instant Indexing 활성화 + URL 제출"""
    base = f"{site_url}/wp-json"
    try:
        # 1. Instant Indexing 플러그인 설정 확인
        r = requests.get(f"{base}/rankmath/v1/getOptions",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        timeout=10)
        
        # 2. 최근 글 URL 수집
        posts_r = requests.get(f"{base}/wp/v2/posts",
                              auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              params={"per_page": 100, "status": "publish",
                                      "_fields": "link", "orderby": "date"},
                              timeout=15)
        
        if posts_r.status_code != 200:
            print(f"    ⚠️ 글 목록 조회 실패")
            return 0
            
        urls = [p.get("link","") for p in posts_r.json() if p.get("link")]
        
        # 3. Rank Math Instant Indexing API로 URL 제출
        submitted = 0
        batch_size = 20
        for i in range(0, min(len(urls), 100), batch_size):
            batch = urls[i:i+batch_size]
            ir = requests.post(
                f"{base}/rankmath/v1/instantIndexing",
                auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                json={"urls": batch, "action": "URL_UPDATED"},
                timeout=20)
            if ir.status_code in (200,201):
                submitted += len(batch)
                
        if submitted:
            print(f"    ✅ Instant Indexing {submitted}개 URL 제출")
        else:
            # Google ping으로 대체
            sitemap = f"{site_url}/sitemap_index.xml"
            ping = f"https://www.google.com/ping?sitemap={requests.utils.quote(sitemap)}"
            requests.get(ping, timeout=8)
            print(f"    ✅ Google Sitemap ping 완료")
            
        return submitted
    except Exception as e:
        print(f"    ⚠️ Instant Indexing 오류: {e}")
        return 0

def allow_indexing(base, pw):
    code,_,_ = api("POST",f"{base}/settings",pw,{"blog_public":True})
    print(f"    {'✅' if code<300 else '⚠️'} 색인 허용 ({code})")
def force_generatepress_premium(site_url: str, pw: str, theme_slug: str = "generatepress"):
    """GeneratePress (Premium) 강제 활성화"""
    try:
        # 현재 활성 테마 확인
        r = requests.get(f"{site_url}/wp-json/wp/v2/themes",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        params={"status": "active"}, timeout=10)
        if r.status_code == 200:
            themes = r.json()
            if isinstance(themes, list):
                for t in themes:
                    slug = t.get("stylesheet","") or t.get("template","")
                    if "generatepress" in slug.lower():
                        print(f"    ✅ GP 이미 활성화됨: {slug}")
                        return True

        # 설치된 테마 목록에서 GP 찾기
        r2 = requests.get(f"{site_url}/wp-json/wp/v2/themes",
                         auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                         timeout=10)
        if r2.status_code == 200:
            all_themes = r2.json()
            if isinstance(all_themes, list):
                for t in all_themes:
                    slug = t.get("stylesheet","") or t.get("template","")
                    if "generatepress" in slug.lower():
                        # 활성화 시도
                        act = requests.post(
                            f"{site_url}/wp-json/wp/v2/themes/{slug}",
                            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                            json={"status": "active"}, timeout=15)
                        if act.status_code in (200,201):
                            print(f"    ✅ GP 활성화 완료: {slug}")
                            return True

        print(f"    ⚠️ GP REST API 활성화 불가 → hPanel에서 수동 확인 필요")
        return False
    except Exception as e:
        print(f"    ⚠️ GP 설치 오류: {e}")
        return False


def fix_duplicate_pages(base: str, pw: str):
    """중복 페이지 삭제 — 같은 slug 중 가장 오래된 것만 유지, 나머지 삭제"""
    all_pages = get_all_pages(base, pw)
    slug_map = {}
    for pg in all_pages:
        slug = pg.get("slug","")
        pid = pg.get("id")
        date = pg.get("date","")
        if slug not in slug_map:
            slug_map[slug] = []
        slug_map[slug].append((pid, date))

    deleted = 0
    for slug, items in slug_map.items():
        if len(items) <= 1:
            continue
        # 날짜순 정렬 — 가장 오래된 것(첫번째) 유지, 나머지 삭제
        items_sorted = sorted(items, key=lambda x: x[1])
        for pid, date in items_sorted[1:]:  # 첫번째 제외 삭제
            code,_,_ = api("DELETE", f"{base}/pages/{pid}", pw, params={"force": True})
            if code in (200,201):
                deleted += 1
                print(f"    🗑️ 중복 페이지 삭제: {slug} (ID:{pid})")
    if deleted:
        print(f"    ✅ 중복 페이지 {deleted}개 삭제 완료")
    return deleted


def setup_menu_and_footer(site_url: str, pw: str, lang: str,
                           cat_ids: list, cat_names: list, page_slugs_map: dict):
    """
    메뉴 2줄 구성:
    - Primary Menu (1줄): 카테고리 4개 (황금3+Etc)
    - Secondary/Top Menu (2줄): 필수 4페이지
    - Footer Menu: 필수 4페이지
    """
    base_wp = f"{site_url}/wp-json"

    try:
        # ── 메뉴 목록 조회 ──
        r = requests.get(f"{base_wp}/wp/v2/menus",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw), timeout=10)
        if r.status_code != 200:
            # menus/v1 시도
            r = requests.get(f"{base_wp}/menus/v1/menus",
                            auth=requests.auth.HTTPBasicAuth(WP_USER, pw), timeout=10)

        menus = r.json() if r.status_code == 200 else []
        if not isinstance(menus, list) or not menus:
            # 메뉴 없으면 새로 생성
            cr = requests.post(f"{base_wp}/wp/v2/menus",
                              auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              json={"name": "Primary Menu", "slug": "primary-menu"},
                              timeout=10)
            if cr.status_code in (200,201):
                menus = [cr.json()]
            else:
                print(f"    ⚠️ 메뉴 생성 실패")
                return

        # 주 메뉴 (첫번째)
        main_menu = menus[0]
        menu_id = main_menu.get("id") or main_menu.get("term_id")

        # Footer 메뉴 찾기 또는 생성
        footer_menu_id = None
        for m in menus:
            name = (m.get("name") or "").lower()
            if "footer" in name:
                footer_menu_id = m.get("id") or m.get("term_id")
                break
        if not footer_menu_id:
            fr = requests.post(f"{base_wp}/wp/v2/menus",
                              auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              json={"name": "Footer Menu", "slug": "footer-menu"},
                              timeout=10)
            if fr.status_code in (200,201):
                footer_menu_id = fr.json().get("id")

        # ── 기존 메뉴 아이템 전부 삭제 후 재구성 ──
        for mid in [menu_id, footer_menu_id]:
            if not mid: continue
            ir = requests.get(f"{base_wp}/wp/v2/menu-items",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             params={"menus": mid, "per_page": 100}, timeout=10)
            if ir.status_code == 200:
                for item in ir.json():
                    requests.delete(f"{base_wp}/wp/v2/menu-items/{item['id']}",
                                   auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                   params={"force": True}, timeout=8)

        # ── 메인메뉴: 황금 카테고리 3+1 ──
        etc_name = "기타" if lang == "ko" else "Etc"
        added_cats = 0
        for cid, cname in zip(cat_ids, cat_names):
            if not cid or cid <= 0: continue
            r = requests.post(f"{base_wp}/wp/v2/menu-items",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             json={"menus": menu_id, "object_id": cid,
                                   "object": "category", "type": "taxonomy",
                                   "status": "publish"}, timeout=10)
            if r.status_code in (200,201):
                added_cats += 1
        print(f"    📋 메인메뉴 카테고리 {added_cats}개 등록")

        # ── Footer: 필수 4페이지 ──
        page_order = ["privacy-policy","disclaimer","contact","about"]
        page_labels = {
            "privacy-policy": "Privacy Policy" if lang=="en" else "개인정보처리방침",
            "disclaimer": "Disclaimer" if lang=="en" else "면책공고",
            "contact": "Contact Us" if lang=="en" else "문의하기",
            "about": "About Us" if lang=="en" else "사이트 소개",
        }
        added_pages = 0
        base_api = f"{site_url}/wp-json/wp/v2"
        for slug in page_order:
            page_id = page_slugs_map.get(slug)
            if not page_id:
                # 직접 조회
                pr = requests.get(f"{base_api}/pages",
                                 auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                 params={"slug": slug, "per_page":1}, timeout=8)
                if pr.status_code == 200 and pr.json():
                    page_id = pr.json()[0]["id"]
            if not page_id: continue

            target_menu = footer_menu_id or menu_id
            r = requests.post(f"{base_wp}/wp/v2/menu-items",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             json={"menus": target_menu, "object_id": page_id,
                                   "object": "page", "type": "post_type",
                                   "title": page_labels.get(slug, slug),
                                   "status": "publish"}, timeout=10)
            if r.status_code in (200,201):
                added_pages += 1
        print(f"    📋 Footer 필수페이지 {added_pages}개 등록")

        # ── 메뉴 위치 등록 (Primary + Footer) ──
        loc_r = requests.post(f"{base_wp}/wp/v2/menu-locations",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             json={"primary": menu_id, "footer": footer_menu_id},
                             timeout=10)

    except Exception as e:
        print(f"    ⚠️ 메뉴 설정 오류: {e}")


def force_install_generatepress(site_url: str, pw: str):
    """GeneratePress 테마 강제 설치 및 활성화"""
    base = f"{site_url}/wp-json/wp/v2"
    
    # 1. 현재 활성 테마 확인
    code, r, _ = api("GET", f"{site_url}/wp-json/wp/v1/themes", pw, 
                     params={"status": "active"})
    if code == 200 and isinstance(r, list) and r:
        current = r[0].get("stylesheet", "")
        print(f"    현재 테마: {current}")
        if "generatepress" in current.lower():
            print(f"    ✅ 이미 GeneratePress 활성화됨")
            return True

    # 2. GeneratePress 설치 (WP CLI via REST)
    # themes endpoint로 설치
    install_r = requests.post(
        f"{site_url}/wp-json/wp/v1/themes",
        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
        json={"slug": "generatepress", "status": "active"},
        timeout=30
    )
    if install_r.status_code in (200, 201):
        print(f"    ✅ GeneratePress 설치·활성화 완료")
        return True
    
    # 3. 이미 설치된 경우 활성화만
    activate_r = requests.post(
        f"{site_url}/wp-json/wp/v1/themes/generatepress",
        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
        json={"status": "active"},
        timeout=20
    )
    if activate_r.status_code in (200, 201):
        print(f"    ✅ GeneratePress 활성화 완료")
        return True
    
    print(f"    ⚠️ REST API 테마 설치 불가 ({install_r.status_code}) → Hostinger에서 수동 설치 필요")
    return False


def register_pages_to_menu(site_url: str, pw: str, lang: str):
    """필수 4페이지를 메인 메뉴에 자동 등록"""
    base = site_url
    try:
        # 메뉴 목록 조회
        r = requests.get(f"{base}/wp-json/wp/v2/menus",
                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                        timeout=10)
        if r.status_code != 200:
            # 메뉴 API 없으면 wp-json/menus/v1 시도
            r = requests.get(f"{base}/wp-json/menus/v1/menus",
                            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                            timeout=10)
        if r.status_code != 200:
            print(f"    ⚠️ 메뉴 API 없음 — 스킵")
            return

        menus = r.json()
        if not menus:
            print(f"    ⚠️ 메뉴 없음")
            return

        menu_id = menus[0].get("id") or menus[0].get("term_id")
        if not menu_id:
            return

        # 등록할 페이지 슬러그 목록
        page_slugs = ["privacy-policy","disclaimer","contact","about"]
        wp_base = f"{site_url}/wp-json/wp/v2"

        for slug in page_slugs:
            # 페이지 ID 조회
            pr = requests.get(f"{wp_base}/pages",
                             auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                             params={"slug": slug, "per_page": 1},
                             timeout=10)
            if pr.status_code != 200 or not pr.json():
                continue
            page_id = pr.json()[0]["id"]
            page_url = pr.json()[0].get("link", "")

            # 메뉴 아이템 등록
            mi = requests.post(f"{site_url}/wp-json/wp/v2/menu-items",
                              auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              json={"menus": menu_id, "object_id": page_id,
                                    "object": "page", "type": "post_type",
                                    "status": "publish"},
                              timeout=10)
            if mi.status_code in (200, 201):
                print(f"    ✅ 메뉴 등록: {slug}")
            elif mi.status_code == 400:
                print(f"    ℹ️ 이미 등록됨: {slug}")
    except Exception as e:
        print(f"    ⚠️ 메뉴 등록 실패: {e}")



# ★ 한글 → 영어 슬러그 변환 테이블
SLUG_MAP = {
    "건강의학정보": "health-medical-info",
    "건강기능식품정보": "health-functional-food",
    "질환별관리법": "disease-management",
    "기타": "etc",
    "경제": "economy",
    "정치": "politics",
    "사회": "society",
    "성형·피부과": "plastic-dermatology",
    "정부지원혜택": "government-support",
    "비용·병원비": "medical-cost",
    "국내주식·etf": "korea-stocks-etf",
    "부동산·청약": "real-estate-subscription",
    "절세·연금": "tax-saving-pension",
    "외국인 건강보험": "foreigner-health-insurance",
    "외국인 자동차보험": "foreigner-auto-insurance",
    "외국인 치과보험": "foreigner-dental-insurance",
    "외국인 은행·송금": "foreigner-banking-remittance",
    "외국인 투자·주식": "foreigner-investment-stocks",
    "외국인 세금·환급": "foreigner-tax-refund",
    "외국인 세금·신고": "foreigner-tax-filing",
    "외국인 법인·창업": "foreigner-corporation-startup",
    "외국인 비자·체류": "foreigner-visa-stay",
    "업비트·거래소 가입": "upbit-exchange-signup",
    "외국인 코인 투자법": "foreigner-crypto-investing",
    "한국 가상화폐 규제": "korea-crypto-regulation",
    "아파트 매매·전세·월세": "apartment-buy-rent",
    "상가·사업장 임대": "commercial-lease",
    "외국인 대출·세금": "foreigner-loan-tax",
    "인기상품 top30": "top30-products",
    "결혼·법적·비자": "marriage-legal-visa",
    "자녀국적·교육혜택": "children-nationality-education",
    "매칭·결혼비용": "matchmaking-wedding-cost",
    "입학정보": "admission-info",
    "장학금": "scholarship",
    "비자": "visa",
}

def slug_of(name):
    key = name.lower().strip()
    if key in SLUG_MAP:
        return SLUG_MAP[key]
    s = name.lower()
    s = re.sub(r'[&·/]', '-', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9\-]', '', s)  # ★ 한글 완전 제거
    s = re.sub(r'-+', '-', s)
    return s.strip('-') or "category"

# ★ 색인 요청 (IndexNow + Search Console ping)
def request_indexing(site_url: str, wp_pass: str):
    """기존 글 전체 색인 요청"""
    base = f"{site_url}/wp-json/wp/v2"
    indexed = 0
    page = 1
    urls = []
    while True:
        code, posts, _ = api("GET", f"{base}/posts", wp_pass,
                             params={"per_page":100,"page":page,"status":"publish","_fields":"link"})
        if code != 200 or not isinstance(posts, list) or not posts: break
        for p in posts:
            link = p.get("link","")
            if link: urls.append(link)
        if len(posts) < 100: break
        page += 1

    # Search Console ping (sitemap)
    domain = site_url.replace("https://","").replace("http://","")
    sitemap_url = f"{site_url}/sitemap_index.xml"
    try:
        ping = f"https://www.google.com/ping?sitemap={requests.utils.quote(sitemap_url)}"
        r = requests.get(ping, timeout=10)
        print(f"    🔍 Sitemap ping: HTTP {r.status_code} → {sitemap_url}")
    except Exception as e:
        print(f"    ⚠️ Sitemap ping 실패: {e}")

    print(f"    📋 색인 요청 대상: {len(urls)}개 URL")
    return len(urls)

def send_to_sheets(records):
    if not SHEETS_WEBHOOK or not records:
        print("  ⚠️ SHEETS_WEBHOOK 없음 — 구글시트 전송 스킵")
        return
    try:
        r = requests.post(SHEETS_WEBHOOK,
                          json={"type":"site_health_report","records":records},
                          timeout=20)
        print(f"\n📊 구글시트 전송 완료 ({len(records)}개 사이트) HTTP {r.status_code}")
    except Exception as e:
        print(f"\n⚠️ 구글시트 전송 실패: {e}")

# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def run():
    report=[]
    total=len(SITES); ok=0; skipped=0
    ts = now_kst()

    print("="*65)
    print(f"🚀 27개 사이트 완전 정리 v4.0  [{ts}]")
    print("★ 황금3 + Etc/기타 = 4개 카테고리 고정")
    print("★ 색인 요청 자동화 포함")
    print("="*65)

    for i, row in enumerate(SITES,1):
        (url,env_key,lang,theme,site_title,
         c1,c2,c3, kws2,kws3,
         fix_idx, robots_ok_default, theme_ok_default) = row

        pw  = os.getenv(env_key,"")
        base= f"{url}/wp-json/wp/v2"
        domain = url.replace("https://","")
        print(f"\n[{i}/{total}] {url}")

        if not pw:
            print(f"  ⚠️ 비밀번호 없음 ({env_key})")
            skipped+=1; continue

        code,_,hdrs = api("GET",f"{base}/posts",pw,params={"per_page":1,"status":"publish"})
        if code==0 or code>=500:
            print(f"  ❌ 접속 불가 (HTTP {code})")
            skipped+=1; continue

        total_posts = int(hdrs.get("X-WP-Total",0))
        print(f"  접속 OK | 포스트 {total_posts}건")

        # [1] 색인 허용
        if fix_idx:
            print("  🔓 색인 차단 해제...")
            allow_indexing(base, pw)

        # [1-0] ★ koreamedicaltour 전용 긴급 정리
        if "koreamedicaltour" in url:
            print("  🚨 koreamedicaltour 한국어글+수술사진 긴급 삭제...")
            cleanup_medicaltour(url, pw)

        # ★ GP Premium 제외 사이트
        skip_gp = any(x in url for x in [
            "koreanews365","theseouljournal","korea365"
        ])

        # [1-1] ★ Elementor 템플릿 완전 삭제
        if not skip_gp:
            print("  🗑️ Elementor 템플릿 삭제...")
            remove_elementor_templates(url, pw)

        # [1-2] ★ GP Premium 강제 활성화
        if not skip_gp:
            print("  🎨 GP Premium 강제 활성화...")
            activate_gp_premium(url, pw)

        # [1-3] ★ 홈페이지 → 최신글 설정
        if not skip_gp:
            print("  🏠 홈페이지 최신글 설정...")
            set_homepage_to_latest_posts(url, pw)

        # [1-4] ★ 언어 설정 (k-health365, koreanews365만 ko)
        print(f"  🌐 언어 설정: {'ko' if lang=='ko' else 'en'}...")
        set_site_language(url, pw, lang)

        # [2] ★ 황금3 + Etc/기타 = 4개 카테고리 생성
        etc_name = "기타" if lang=="ko" else "Etc"
        print(f"  📁 카테고리: {c1} / {c2} / {c3} / {etc_name}")
        id1=get_or_create_cat(base,pw,c1,slug_of(c1))
        id2=get_or_create_cat(base,pw,c2,slug_of(c2))
        id3=get_or_create_cat(base,pw,c3,slug_of(c3))
        id4=get_or_create_cat(base,pw,etc_name,slug_of(etc_name))
        keep_ids=[x for x in [id1,id2,id3,id4] if x]

        # [2-1] ★ 기본 카테고리를 황금1번으로 설정 (기존 default 카테고리 삭제 가능하게)
        if id1:
            api("POST",f"{base}/settings",pw,{"default_category": id1})

        # [3] 포스트 재배분
        if keep_ids and total_posts>0:
            print(f"  📝 포스트 재배분 ({total_posts}건)...")
            reassign_posts_fast(base,pw,id1,id2,id3,id4,kws2,kws3)

        # [4] ★ 불필요 카테고리 전부 삭제
        print("  🗑️ 카테고리 정리 (황금4 외 전부 삭제)...")
        all_cats=get_all_cats(base,pw)
        deleted=0
        for cat in all_cats:
            cid=cat.get("id")
            if cid in keep_ids or cid==1: continue
            fallback=id1 if id1 else 1
            if delete_cat_force(base,pw,cid,fallback): deleted+=1
        if deleted: print(f"    🗑️ {deleted}개 불필요 카테고리 삭제 완료")

        # [5] 필수 4페이지
        print("  📄 페이지 정리...")
        all_pages=get_all_pages(base,pw)
        del_pages=0
        for pg in all_pages:
            pg_slug=pg.get("slug","")
            is_keep=any(pg_slug==s or pg_slug.startswith(s) for s in KEEP_PAGE_SLUGS)
            if not is_keep:
                api("DELETE",f"{base}/pages/{pg['id']}",pw,params={"force":True})
                del_pages+=1
        if del_pages: print(f"    {del_pages}개 불필요 페이지 삭제")

        for ptitle,pslug,pcontent in required_pages(lang):
            upsert_page(base,pw,ptitle,pslug,pcontent)

        pg_check = check_pages(base, pw)
        has_p = pg_check["privacy"]
        has_a = pg_check["about"]
        has_c = pg_check["contact"]
        has_d = pg_check["disclaimer"]
        pages4_ok = all([has_p,has_a,has_c,has_d])
        print(f"    Privacy:{'✅' if has_p else '❌'} About:{'✅' if has_a else '❌'} Contact:{'✅' if has_c else '❌'} Disclaimer:{'✅' if has_d else '❌'}")

        # [6] 사이트명
        api("POST",f"{base}/settings",pw,{"title":site_title})

        # [6-0] ★ ads.txt 자동 삽입
        print("  📄 ads.txt 삽입...")
        fix_ads_txt(url, pw)

        # [6-1] ★ 중복 페이지 삭제
        print("  🗑️ 중복 페이지 정리...")
        fix_duplicate_pages(base, pw)

        # [6-2] ★ 2줄 메뉴 자동 구성 + CSS 삽입
        print("  📋 2줄 메뉴 구성 (카테고리줄 + 페이지줄)...")
        pg_map = {}
        for s in ["privacy-policy","disclaimer","contact","about"]:
            pr = requests.get(f"{base}/pages",
                             auth=requests.auth.HTTPBasicAuth(WP_USER,pw),
                             params={"slug":s,"per_page":1}, timeout=8)
            if pr.status_code==200 and pr.json():
                pg_map[s] = pr.json()[0]["id"]
        setup_dual_menu(url, pw, lang,
                        [id1,id2,id3,id4],
                        [c1,c2,c3,etc_name],
                        pg_map)

        # [6-3] ★ 메뉴 CSS 삽입
        print("  🎨 메뉴 CSS 삽입...")
        inject_menu_css(url, pw)

        # [7] ★ GitHub Actions IP 허용 코드 삽입
        print("  🔓 GitHub Actions IP 허용...")
        install_github_ip_whitelist(url, pw)

        # [8] ★ Rank Math Instant Indexing
        print("  🔍 Rank Math Instant Indexing...")
        setup_rank_math_indexing(url, pw)

        # [9] ★ SEO 상태 확인
        print("  📊 SEO 확인...")
        verify_post_seo(url, pw, limit=10)

        # [9-1] ★ 기존 글 noindex 제거
        print("  🔧 기존 글 noindex 제거...")
        fix_post_noindex_and_404(url, pw)

        # [9-2] ★ 저품질 글 정리 (연도/중복/주제이탈/800자미만)
        print("  🗑️ 저품질 글 정리 v2.0...")
        audit_and_clean_posts(url, pw, lang, dry_run=False)

        # [9-3] ★ SEO 90점 이하 삭제
        print("  🗑️ SEO 90점 이하 삭제...")
        deleted_low = 0
        page_s = 1
        while True:
            try:
                rs = requests.get(f"{base}/posts",
                               auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                               params={"per_page":50,"page":page_s,"status":"publish",
                                       "_fields":"id,meta,title"},
                               timeout=15)
                if rs.status_code != 200 or not rs.json(): break
                posts_s = rs.json()
                for post_s in posts_s:
                    meta_s = post_s.get("meta", {})
                    score_s = meta_s.get("rank_math_seo_score", "")
                    try:
                        score_int = int(float(str(score_s))) if score_s else 0
                    except:
                        score_int = 0
                    if 0 < score_int < 90:
                        dr = requests.delete(f"{base}/posts/{post_s['id']}",
                                            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                            params={"force": True}, timeout=10)
                        if dr.status_code in (200, 201):
                            deleted_low += 1
                if len(posts_s) < 50: break
                page_s += 1
            except: break
        if deleted_low:
            print(f"    ✅ SEO 90점 이하 {deleted_low}건 삭제")

        # [10] ★ 검색엔진 ping
        print("  🔍 검색엔진 ping...")
        ping_search_engines(url)

        # 최종 카테고리 수 확인
        final_cats=[c for c in get_all_cats(base,pw) if c.get("id")!=1]
        cat_count=len(final_cats)

        noindex_ok = check_noindex(url)
        if noindex_ok is None: noindex_ok = robots_ok_default

        adsense_score, adsense_grade = calc_adsense_grade(
            total_posts, cat_count, pages4_ok,
            robots_ok_default, noindex_ok if noindex_ok else False,
            theme_ok_default, has_p, has_a, has_c, has_d
        )

        urgent=[]
        if not robots_ok_default: urgent.append("robots.txt 차단해제")
        if noindex_ok==False: urgent.append("noindex 제거")
        if not theme_ok_default: urgent.append("테마 교체 필요")
        if total_posts<15: urgent.append(f"포스트 부족({total_posts}건→15건 이상)")
        if cat_count!=4: urgent.append(f"카테고리 {cat_count}개→4개로 조정")
        if not pages4_ok:
            missing=[k for k,v in pg_check.items() if not v]
            urgent.append(f"페이지 누락: {','.join(missing)}")
        urgent_str = " | ".join(urgent) if urgent else "없음 ✅"

        rec = {
            "순위":i, "도메인":domain, "테마":theme, "언어":lang,
            "사이트명":site_title,
            "카테고리1":c1, "카테고리2":c2, "카테고리3":c3,
            "발행글수":total_posts, "카테고리수":cat_count,
            "Privacy":"O" if has_p else "X",
            "About":"O" if has_a else "X",
            "Contact":"O" if has_c else "X",
            "Disclaimer":"O" if has_d else "X",
            "필수4페이지":"✅ 완비" if pages4_ok else "❌ 미완",
            "색인가능":"✅" if (robots_ok_default and noindex_ok!=False) else "❌ 차단",
            "테마정상":"✅" if theme_ok_default else "❌ 교체필요",
            "AdSense점수":adsense_score, "AdSense등급":adsense_grade,
            "AdSense상태":"준비됨·승인됨" if domain=="k-health365.com" else "준비중-찾을수없음",
            "긴급조치":urgent_str, "상태":"✅ 완료", "업데이트시각":ts,
        }
        report.append(rec)
        print(f"  ✅ 완료 | 카테고리 {cat_count}개 | AdSense {adsense_grade}등급({adsense_score}점)")
        ok+=1
        time.sleep(1)

    print("\n"+"="*65)
    print("📊 27개 사이트 종합 건강 리포트")
    print("="*65)
    hdr=f"{'#':<3} {'도메인':<28} {'글':>5} {'카':>3} {'4P':>4} {'색인':>4} {'등급':>4} {'점수':>4}"
    print(hdr); print("-"*65)
    for r in sorted(report,key=lambda x:x.get("AdSense점수",0),reverse=True):
        pages_icon="✅" if "완비" in r.get("필수4페이지","") else "❌"
        idx_icon="✅" if "✅" in r.get("색인가능","") else "❌"
        print(f"{r['순위']:<3} {r['도메인']:<28} {r.get('발행글수',0):>5} "
              f"{r.get('카테고리수',0):>3} {pages_icon:>4} {idx_icon:>4} "
              f"{r.get('AdSense등급','?'):>4} {r.get('AdSense점수',0):>4}점")
    print("-"*65)
    print(f"✅ 성공:{ok} | ⚠️ 스킵:{skipped} | 총:{total}")

    send_to_sheets(report)

if __name__=="__main__":
    run()
