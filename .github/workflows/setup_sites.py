#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_sites.py v2.1 — 27개 사이트 완전 정리
수정: 타임아웃 방어 + 삭제실패 카테고리 강제처리 + 배치재배분
"""

import os, time, re, requests

WP_USER = "huh0303@gmail.com"
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

# ════════════════════════════════════════════════════════════
# 27개 사이트 설정
# ════════════════════════════════════════════════════════════
SITES = [
  ("https://k-health365.com","KHEALTH365COM","ko","K-Health365 건강정보",
   "건강의학정보","건강기능식품정보","질환별관리법",
   ["영양제","비타민","유산균","보충제","기능성","콜라겐","오메가","다이어트","체중","식품"],
   ["혈압","당뇨","혈당","암","피부","아토피","탈모","관절","허리","디스크","골다공증","수면","불면","우울","치료","예방","관리"],
   False),
  ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM","en","Korea Medical Tour",
   "Surgery","Dental","Dermatology",
   ["dental","teeth","orthodontics","implant","whitening"],
   ["dermatology","skin","laser","botox","filler","acne","aesthetics"],
   False),
  ("https://koreainvest365.com","KOREAINVEST365COM","en","Korea Invest 365",
   "Stocks","Real Estate","Funds",
   ["real estate","property","apartment","jeonse","housing"],
   ["ETF","fund","mutual","index fund","bond","crypto"],
   False),
  ("https://ki-korea.com","KIKOREACOM","ko","KI Korea 한국투자",
   "주식","부동산","절세",
   ["부동산","아파트","청약","분양","전세"],
   ["절세","세금","IRP","연금","비과세","공제"],
   False),
  ("https://koreainsurance365.com","KOREAINSURANCE365COM","en","Korea Insurance 365",
   "Health Insurance","Life Insurance","Auto Insurance",
   ["life","death","term","whole life","accident"],
   ["car","auto","vehicle","driver","traffic"],
   False),
  ("https://kfinance365.com","KFINANCE365COM","en","Korea Finance 365",
   "Banking","Investing","Taxes",
   ["invest","stock","ETF","portfolio","dividend","fund"],
   ["tax","income tax","VAT","refund","deduction"],
   False),
  ("https://koreataxnlaw.com","KOREATAXNLAWCOM","en","Korea Tax & Law",
   "Taxes","Business","Visas",
   ["business","company","startup","registration","corporate"],
   ["visa","immigration","residence","permit","foreigner"],
   False),
  ("https://koreacrypto365.com","KOREACRYPTO365COM","en","Korea Crypto 365",
   "Bitcoin","Exchanges","Regulation",
   ["exchange","upbit","bithumb","binance","trading"],
   ["regulation","law","FSC","SEC","tax","legal","compliance"],
   False),
  ("https://krealestate365.com","KREALESTATE365COM","ko","한국부동산 정석",
   "아파트","투자","세금",
   ["투자","전략","수익","리츠","경매","갭투자"],
   ["세금","취득세","양도세","재산세","증여","상속"],
   True),
  ("https://ktech365.com","KTECH365COM","en","KTech365 Korea Tech",
   "AI","Startups","Semiconductors",
   ["startup","venture","unicorn","founder","funding"],
   ["semiconductor","chip","TSMC","fab","wafer","memory"],
   False),
  ("https://kskin365.com","KSKIN365COM","en","KSkin365 K-Beauty",
   "Skincare","Ingredients","Routines",
   ["ingredient","niacinamide","hyaluronic","retinol","vitamin C","peptide"],
   ["routine","steps","morning","night","layering"],
   False),
  ("https://oliveyoungkorea.com","OLIVEYOUNGKOREACOM","en","Olive Young Korea",
   "Skincare","Makeup","Haircare",
   ["makeup","foundation","lipstick","blush","eyeshadow","concealer"],
   ["hair","shampoo","scalp","conditioner","treatment"],
   False),
  ("https://kworld365.com","KWORLD365COM","en","KWorld365 K-POP",
   "Artists","Music","Tours",
   ["album","release","comeback","single","MV","music"],
   ["concert","tour","performance","live","show"],
   True),
  ("https://k-trip365.com","KTRIP365COM","en","K-Trip365 Korea Travel",
   "Travel Guides","Food","Hotels",
   ["food","restaurant","cuisine","street food","dish","cafe"],
   ["hotel","accommodation","stay","hostel","airbnb"],
   False),
  ("https://k-visa365.com","KVISA365COM","en","K-Visa365 Korea Visa",
   "Work Visa","Student Visa","Long-term Visa",
   ["student","D-2","D-4","language school","university"],
   ["F-2","F-5","long-term","permanent","settlement"],
   False),
  ("https://koreawedding365.com","KOREAWEDDING365COM","en","Korea Wedding 365",
   "Planning","Venues","Legal",
   ["venue","hall","location","ceremony","outdoor"],
   ["legal","registration","document","certificate","marriage law"],
   False),
  ("https://kstudy365.com","KSTUDY365COM","en","KStudy365 Study in Korea",
   "Study Korea","Scholarships","Student Life",
   ["scholarship","GKS","KGSP","funding","stipend","award"],
   ["student life","campus","dorm","visa","part-time"],
   False),
  ("https://studyinkorea365.com","STUDYINKOREA365COM","en","Study in Korea 365",
   "Admissions","Scholarships","Campus Life",
   ["scholarship","GKS","government","KGSP","funding","financial aid"],
   ["campus","dormitory","housing","student life","clubs"],
   False),
  ("https://kieca-korea.org","KIECAKOREAORG","en","KIECA Korea",
   "Language","Culture","Careers",
   ["culture","tradition","exchange","festival","history","art"],
   ["career","job","work","internship","employment"],
   False),
  ("https://ksa-korea.org","KSAKOREAORG","ko","KSA Korea 한국유학협회",
   "입학정보","장학금","비자",
   ["장학금","GKS","정부초청","지원금","면제"],
   ["비자","D-2","출입국","체류","연장"],
   True),
  ("https://sis-korea.com","SISKOREACOM","en","SIS Korea",
   "Programs","Scholarships","TOPIK",
   ["scholarship","fee","funding","financial","tuition"],
   ["TOPIK","Korean test","language exam","proficiency","test prep"],
   False),
  ("https://jobkorea365.com","JOBKOREA365COM","en","Job Korea 365",
   "Jobs","Salaries","Work Visa",
   ["salary","wage","income","pay","compensation","benefits"],
   ["visa","E-7","work permit","eligibility","sponsor"],
   False),
  ("https://jobinkorea365.com","JOBINKOREA365COM","en","Jobs in Korea 365",
   "Jobs","Interviews","Salaries",
   ["interview","preparation","question","answer","tips","STAR"],
   ["salary","wage","negotiation","pay","compensation"],
   False),
  ("https://jobkoreaglobal.com","JOBKOREAGLOBALCOM","en","Job Korea Global",
   "Hiring","Salaries","Foreign Workers",
   ["salary","compensation","benefits","pay scale","benchmark"],
   ["foreign worker","EPS","H-2","E-9","migrant","overseas"],
   False),
  ("https://korea365.org","KOREA365ORG","en","Korea 365",
   "Korean Culture","Travel & Food","Living in Korea",
   ["travel","food","restaurant","cuisine","trip","tourism"],
   ["living","expat","foreigner","daily","tips","cost"],
   False),
  ("https://koreanews365.com","KOREANEWS365COM","ko","한국타임즈",
   "경제","정치","사회",
   ["정치","대통령","국회","선거","외교","북한","여당","야당"],
   ["사회","범죄","복지","교육","문화","국제","IT","반도체"],
   False),
  ("https://theseouljournal.com","THESEOULJOURNALCOM","en","The Seoul Journal",
   "Politics","Economy","Culture",
   ["economy","market","stock","trade","business","finance","GDP"],
   ["culture","K-pop","music","food","lifestyle","travel","expat"],
   False),
]

# ── API 함수 ──────────────────────────────────────────────
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

def find_existing_wp_category(base, pw, name, slug):
    """기존 카테고리에서 찾기 (생성 전 확인)"""
    code,r,_ = api("GET",f"{base}/categories",pw,params={"slug":slug,"per_page":1})
    if isinstance(r,list) and r: return r[0]["id"]
    code,r,_ = api("GET",f"{base}/categories",pw,params={"search":name,"per_page":10})
    if isinstance(r,list):
        for c in r:
            if c.get("name","").strip().lower()==name.strip().lower():
                return c["id"]
    return None

def get_or_create_cat(base, pw, name, slug):
    existing = find_existing_wp_category(base, pw, name, slug)
    if existing: return existing
    code,r,_ = api("POST",f"{base}/categories",pw,{"name":name,"slug":slug,"description":f"{name} category"})
    if code in(200,201) and r.get("id"):
        print(f"    ✅ 생성: {name}")
        return r["id"]
    # 재시도
    existing = find_existing_wp_category(base, pw, name, slug)
    if existing: return existing
    print(f"    ⚠️ 카테고리 실패: {name}")
    return None

def delete_cat(base, pw, cat_id):
    """포스트를 먼저 이동한 뒤 삭제 시도"""
    code,_,_ = api("DELETE",f"{base}/categories/{cat_id}",pw,params={"force":True})
    return code in(200,201)

def reassign_posts_fast(base, pw, id1, id2, id3, kws2, kws3, max_posts=1000):
    """배치 재배분 — 타임아웃 방어용 (페이지당 처리 후 즉시 다음)"""
    page=1; moved=0
    while moved < max_posts:
        code,posts,hdrs = api("GET",f"{base}/posts",pw,
                               params={"per_page":50,"page":page,"status":"publish",
                                       "_fields":"id,title,categories"},timeout=25)
        if code!=200 or not isinstance(posts,list) or not posts: break
        for post in posts:
            title_lower = (post.get("title",{}).get("rendered","") or "").lower()
            cur = post.get("categories",[])
            if len(cur)==1 and cur[0] in [id1,id2,id3]: continue
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

def delete_cat_force(base, pw, cat_id, fallback_id):
    """포스트를 fallback으로 옮긴 뒤 삭제"""
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
    if isinstance(r,list) and r: return
    code,_,_ = api("POST",f"{base}/pages",pw,
                   {"title":title,"slug":slug,"content":content,"status":"publish"})
    print(f"    {'✅' if code in(200,201) else '⚠️'} 페이지: {title}")

def allow_indexing(base, pw):
    code,_,_ = api("POST",f"{base}/settings",pw,{"blog_public":True})
    print(f"    {'✅' if code<300 else '⚠️'} 색인 허용 ({code})")

def slug_of(name):
    s=name.lower()
    s=re.sub(r'[&]','and',s)
    s=re.sub(r'\s+','-',s)
    s=re.sub(r'[^a-z0-9가-힣\-]','',s)
    return s.strip('-')

# ── Google Sheets 로깅 ─────────────────────────────────────
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK","")

def log_to_sheets(records):
    if not SHEETS_WEBHOOK or not records: return
    try:
        requests.post(SHEETS_WEBHOOK,
                      json={"type":"setup_report","records":records},
                      timeout=15)
        print(f"  📊 구글시트 전송: {len(records)}건")
    except Exception as e:
        print(f"  ⚠️ 구글시트 전송 실패: {e}")

# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def run():
    report=[]
    total=len(SITES); ok=0; skipped=0
    print("="*60)
    print("🚀 27개 사이트 완전 정리 v2.1 (타임아웃 방어판)")
    print("="*60)

    for i, row in enumerate(SITES,1):
        (url,env_key,lang,site_title,
         c1,c2,c3, kws2,kws3, fix_idx) = row
        pw  = os.getenv(env_key,"")
        base= f"{url}/wp-json/wp/v2"
        print(f"\n[{i}/{total}] {url}")

        if not pw:
            print(f"  ⚠️ 비밀번호 없음 ({env_key})")
            report.append({"url":url,"status":"skip_no_pw","posts":0,"cats":0})
            skipped+=1; continue

        # 접속확인
        code,_,hdrs = api("GET",f"{base}/posts",pw,params={"per_page":1,"status":"publish"})
        if code==0 or code>=500:
            print(f"  ❌ 접속 불가 (HTTP {code})")
            report.append({"url":url,"status":"error","posts":0,"cats":0})
            skipped+=1; continue

        total_posts = int(hdrs.get("X-WP-Total",0))
        print(f"  접속 OK | 포스트 {total_posts}건")

        # [1] 색인 허용
        if fix_idx:
            print("  🔓 색인 차단 해제...")
            allow_indexing(base, pw)

        # [2] 황금 카테고리 3개 생성
        print(f"  📁 카테고리: {c1} / {c2} / {c3}")
        id1=get_or_create_cat(base,pw,c1,slug_of(c1))
        id2=get_or_create_cat(base,pw,c2,slug_of(c2))
        id3=get_or_create_cat(base,pw,c3,slug_of(c3))
        keep_ids=[x for x in [id1,id2,id3] if x]

        # [3] 포스트 재배분 (먼저 해야 삭제 가능)
        if keep_ids and total_posts>0:
            print(f"  📝 포스트 재배분 중 ({total_posts}건)...")
            reassign_posts_fast(base,pw,id1,id2,id3,kws2,kws3,max_posts=total_posts+10)

        # [4] 불필요 카테고리 삭제
        print("  🗑️ 카테고리 정리...")
        all_cats=get_all_cats(base,pw)
        deleted=0; fail_ids=[]
        for cat in all_cats:
            cid=cat.get("id")
            if cid in keep_ids or cid==1: continue
            # 강제 삭제 (포스트 먼저 이동)
            fallback=id1 if id1 else 1
            if delete_cat_force(base,pw,cid,fallback):
                deleted+=1
            else:
                fail_ids.append(f"{cat.get('name')}(ID:{cid})")
        if fail_ids:
            print(f"    ⚠️ 삭제 실패 (무시): {', '.join(fail_ids[:3])}")
        print(f"    {deleted}개 삭제 완료")

        # [5] 페이지 정리 + 필수 4페이지
        print("  📄 페이지 정리...")
        all_pages=get_all_pages(base,pw)
        del_pages=0
        for pg in all_pages:
            pg_slug=pg.get("slug","")
            is_keep=any(pg_slug==s or pg_slug.startswith(s) for s in KEEP_PAGE_SLUGS)
            if not is_keep:
                api("DELETE",f"{base}/pages/{pg['id']}",pw,params={"force":True})
                del_pages+=1
        print(f"    {del_pages}개 불필요 페이지 삭제")

        for ptitle,pslug,pcontent in required_pages(lang):
            upsert_page(base,pw,ptitle,pslug,pcontent)

        # [6] 사이트명
        api("POST",f"{base}/settings",pw,{"title":site_title})
        print(f"  🏷️ 사이트명: {site_title}")

        # [7] 메뉴 정리
        _,menus,_ = api("GET",f"{url}/wp-json/wp/v2/menus",pw)
        if isinstance(menus,list) and menus:
            mid=menus[0]["id"]
            _,items,_ = api("GET",f"{url}/wp-json/wp/v2/menu-items",pw,
                            params={"menu":mid,"per_page":100})
            if isinstance(items,list):
                for item in items:
                    if (item.get("type")=="taxonomy"
                            and item.get("object")=="category"
                            and item.get("object_id") not in keep_ids):
                        api("DELETE",f"{url}/wp-json/wp/v2/menu-items/{item['id']}",
                            pw,params={"force":True})
            for cid in keep_ids:
                if cid:
                    api("POST",f"{url}/wp-json/wp/v2/menu-items",pw,
                        {"menu_id":mid,"object_id":cid,"object":"category",
                         "type":"taxonomy","status":"publish"})

        # 최종 카테고리 수
        final_cats=[c for c in get_all_cats(base,pw) if c.get("id")!=1]
        cat_names=[c.get("name","") for c in final_cats]

        report.append({
            "url":url,"status":"ok","posts":total_posts,
            "cats":len(final_cats),"cat_names":", ".join(cat_names),
            "site_title":site_title,
        })
        print(f"  ✅ 완료 | 카테고리 {len(final_cats)}개: {cat_names}")
        ok+=1
        time.sleep(1)

    # ── 최종 리포트 ────────────────────────────────────────
    print("\n"+"="*60)
    print("📊 색인 발행 현황 리포트 (포스트 수 기준)")
    print("="*60)
    print(f"{'#':<3} {'도메인':<30} {'포스트':>6} {'카테':>4} {'상태':<5} 카테고리명")
    print("-"*60)
    sorted_r=sorted(report,key=lambda x:x.get("posts",0),reverse=True)
    for idx,r in enumerate(sorted_r,1):
        domain=r["url"].replace("https://","")
        st={"ok":"✅","skip_no_pw":"⚠️","error":"❌"}.get(r["status"],"?")
        cats=r.get("cat_names","")[:35]
        print(f"{idx:<3} {domain:<30} {r.get('posts',0):>6}건 {r.get('cats',0):>3}개 {st}  {cats}")
    print("-"*60)
    print(f"✅ 성공:{ok} | ⚠️ 스킵:{skipped} | 총:{total}")

    # 구글시트 전송
    log_to_sheets(report)

    print("\n📌 다음 단계:")
    print("  1. Actions → step=post 로 글 발행 시작")
    print("  2. Google Search Console → 각 사이트 sitemap 제출")
    print("  3. AdSense → 각 사이트 재심사 요청")

if __name__=="__main__":
    run()
