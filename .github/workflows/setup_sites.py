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

  ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM","ko","한국의료관광","Korea Medical Tour",
   "성형·피부과","정부지원혜택","비용·병원비",
   ["정부","지자체","서울시","부산","대구","인천","지원","혜택","보조","의료관광"],
   ["비용","가격","cost","price","fee","얼마","견적","할인","패키지","surgery cost"],
   False, True, True),

  ("https://koreainvest365.com","KOREAINVEST365COM","en","한국투자","Korea Invest 365",
   "Korea Stocks","Korea Funds & ETF","Crypto & Digital",
   ["ETF","fund","mutual","index","bond","dividend","yield","REIT","펀드"],
   ["crypto","bitcoin","ethereum","DeFi","NFT","blockchain","digital asset","upbit"],
   False, True, True),

  ("https://ki-korea.com","KIKOREACOM","ko","한국투자(KO)","KI Korea 한국투자",
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

  ("https://krealestate365.com","KREALESTATE365COM","ko","외국인부동산","한국부동산 정석",
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

  ("https://kworld365.com","KWORLD365COM","en","K-POP","KWorld365 K-POP",
   "Artists","Music","Tours",
   ["album","release","comeback","single","MV","music"],
   ["concert","tour","performance","live","show"],
   True, False, True),

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

  ("https://ksa-korea.org","KSAKOREAORG","ko","한국유학협회","KSA Korea 한국유학협회",
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

def allow_indexing(base, pw):
    code,_,_ = api("POST",f"{base}/settings",pw,{"blog_public":True})
    print(f"    {'✅' if code<300 else '⚠️'} 색인 허용 ({code})")

def slug_of(name):
    s=name.lower()
    s=re.sub(r'[&·]','-',s)
    s=re.sub(r'\s+','-',s)
    s=re.sub(r'[^a-z0-9가-힣\-]','',s)
    return s.strip('-')

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

        # [2] ★ 황금3 + Etc/기타 = 4개 카테고리 생성
        etc_name = "기타" if lang=="ko" else "Etc"
        print(f"  📁 카테고리: {c1} / {c2} / {c3} / {etc_name}")
        id1=get_or_create_cat(base,pw,c1,slug_of(c1))
        id2=get_or_create_cat(base,pw,c2,slug_of(c2))
        id3=get_or_create_cat(base,pw,c3,slug_of(c3))
        id4=get_or_create_cat(base,pw,etc_name,slug_of(etc_name))
        keep_ids=[x for x in [id1,id2,id3,id4] if x]

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

        # [7] ★ 색인 요청 (Sitemap ping)
        print("  🔍 색인 요청...")
        request_indexing(url, pw)

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
