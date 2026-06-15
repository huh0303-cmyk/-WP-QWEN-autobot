import os
import sys
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# 환경 변수 및 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY    = os.getenv("PIXABAY_KEY")
PEXELS_KEY     = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK")
WP_USER        = "huh0303@gmail.com"

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 10인 가상 기자단 풀
REPORTERS = [
    "김민준 기자 (minjun@kworld365.com)", "이서연 기자 (seoyeon@kworld365.com)",
    "박현우 기자 (hyunwoo@kworld365.com)", "최지아 기자 (jia@kworld365.com)",
    "정재희 기자 (jaehee@kworld365.com)", "James Wilson (james@kworld365.com)",
    "Emily Anderson (emily@kworld365.com)", "Michael Chang (michael@kworld365.com)",
    "Sarah Jenkins (sarah@kworld365.com)", "David Miller (david@kworld365.com)"
]

HEALTH_CATEGORIES = [2, 3, 4, 5, 6]

# 대표님이 설정하신 깃허브 Secret 이름과 100% 일치하도록 바인딩 이름 수정 완료
SITES_CONFIG = [
    {"url": "https://k-health365.com",      "type": "hub",  "lang": "ko", "theme": "건강과 의학", "keywords_file": ".github/workflows/keywords_khealth.txt", "wp_pass_env": "K_HEALTH365COM"},
    {"url": "https://koreanews365.com",      "type": "news", "lang": "ko", "theme": "한국 뉴스",   "keywords_file": ".github/workflows/keywords_koreanews.txt", "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",   "type": "global","lang": "en", "theme": "Seoul Lifestyle", "keywords_file": ".github/workflows/keywords_seouljournal.txt", "wp_pass_env": "THESEOULJOURNALCOM"},
    {"url": "https://koreamedicaltour.com",  "type": "global","lang": "en", "theme": "Korea Medical Tourism", "keywords_file": ".github/workflows/keywords_medicaltour.txt", "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://kskin365.com",          "type": "global","lang": "en", "theme": "K-Beauty",   "keywords_file": ".github/workflows/keywords_kskin.txt", "wp_pass_env": "KSKIN365COM"},
    {"url": "https://korea365.org",          "type": "global","lang": "en", "theme": "Korea Culture", "keywords_file": ".github/workflows/keywords_korea365.txt", "wp_pass_env": "KOREA365ORG"},
    {"url": "https://jobinkorea365.com",     "type": "global","lang": "en", "theme": "Jobs in Korea", "keywords_file": ".github/workflows/keywords_jobinkorea365.txt", "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkorea365.com",       "type": "global","lang": "en", "theme": "Employment", "keywords_file": ".github/workflows/keywords_jobkorea365.txt", "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",    "type": "global","lang": "en", "theme": "Recruitment", "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt", "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://kstudy365.com",         "type": "global","lang": "en", "theme": "Study in Korea", "keywords_file": ".github/workflows/keywords_kstudy365.txt", "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea.com",      "type": "global","lang": "en", "theme": "International Students", "keywords_file": ".github/workflows/keywords_koreanews.txt", "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kfinance365.com",       "type": "global","lang": "en", "theme": "Finance",    "keywords_file": ".github/workflows/keywords_kfinance.txt", "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreainvest365.com",    "type": "global","lang": "en", "theme": "Investment", "keywords_file": ".github/workflows/keywords_kinvest.txt", "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://koreataxnlaw.com",      "type": "global","lang": "en", "theme": "Tax and Law", "keywords_file": ".github/workflows/keywords_ktax.txt", "wp_pass_env": "KOREATAXNLAW365COM"},
    {"url": "https://k-trip365.com",         "type": "global","lang": "en", "theme": "Travel",     "keywords_file": ".github/workflows/keywords_ktrip.txt", "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",         "type": "global","lang": "en", "theme": "Visa Guide", "keywords_file": ".github/workflows/keywords_kvisa.txt", "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreacrypto365.com",    "type": "global","lang": "en", "theme": "Crypto",     "keywords_file": ".github/workflows/keywords_kcrypto.txt", "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://koreainsurance365.com", "type": "global","lang": "en", "theme": "Insurance",  "keywords_file": ".github/workflows/keywords_kinsurance.txt", "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://koreavedding365.com",   "type": "global","lang": "en", "theme": "Wedding",    "keywords_file": ".github/workflows/keywords_kwedding.txt", "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://ktech365.com",          "type": "global","lang": "en", "theme": "Technology", "keywords_file": ".github/workflows/keywords_ktech.txt", "wp_pass_env": "KTECH365COM"},
    {"url": "https://kworld365.com",         "type": "global","lang": "en", "theme": "K-POP",      "keywords_file": ".github/workflows/keywords_kworld.txt", "wp_pass_env": "KWORLD365COM"},
    {"url": "https://oliveyoungkorea.com",   "type": "global","lang": "en", "theme": "K-Beauty Reviews", "keywords_file": ".github/workflows/keywords_oliveyoung.txt", "wp_pass_env": "OLIVEYOUNGKOREACOM"},
]

def load_keyword(filename, fallback):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                keywords = [l.strip() for l in f if l.strip()]
            if keywords: return random.choice(keywords)
    except: pass
    return fallback

def crawl_rss_news():
    try:
        res = requests.get("https://fs.khan.co.kr/rss/rssdata/total_news.xml", timeout=10)
        soup = BeautifulSoup(res.text, 'xml')
        items = soup.find_all('item')
        if items:
            chosen = random.choice(items)
            return chosen.title.text, chosen.description.text
    except: pass
    return "대한민국 최신 경제 및 사회 변화 트렌드 분석", "최신 주요 시사 이슈 및 정책 변화에 대한 심층 기사입니다."

def make_seo_prompt(keyword, theme, lang, mode="blog"):
    reporter = random.choice(REPORTERS)
    if mode == "news":
        return f"""
        당신은 주요 일간지의 시니어 취재기자입니다.
        주제: '{keyword}'에 대해 엄격한 신문기사체 기사를 작성하세요.
        
        [필수 지침]
        1. 문체: 절대 블로그 형식을 쓰지 마십시오. '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체여야 합니다.
        2. 바이라인: 기사 맨 위에 반드시 '◇ {reporter}'를 한 줄 삽입하십시오.
        3. 분량 및 구조: HTML 태그(h2, h3, p, strong)만 사용해 1500자 내외로 명확하고 간결하게 작성하세요. 마크다운 금지.
        4. 내용: 첫 단락에 핵심 리드문을 작성하고, 전문적인 인터뷰 인용구나 통계 수치를 가상으로 포함하여 신뢰도를 극대화하십시오.
        """
    
    persona = "의학 박사" if "건강" in theme or "medical" in theme.lower() else "산업 분야 최고 전문 자문위원"
    return f"""
    당신은 {persona}이자 15년 경력의 SEO 콘텐츠 마스터 프로라이터입니다.
    주제: '{keyword}' ({theme})
    언어: {lang}
    
    [구글 애드센스 평가 고득점 핵심 지침]
    1. HTML 전용: 오직 h2, h3, p, ul, li, ol, strong 태그만 사용하고 마크다운(*)은 절대 쓰지 마세요.
    2. 키워드 최적화: 첫 단락 문두에 '{keyword}'를 무조건 배치하고, 전체 글에 자연스럽게 10회 이상 분산 삽입하세요.
    3. 구조 다각화: h2 태그 최소 4개 이상, h3 태그 최소 4개 이상 배치하고, 가독성을 위한 불릿 포인트(ul/li) 리스트를 3개 이상 쪼개어 구성하세요.
    4. 정보량: 깊이 있고 유용한 가치를 주기 위해 상세한 설명글로만 가득 채우십시오.
    """

def get_multiple_images(keyword, count=3):
    urls = []
    try:
        q = keyword.encode('ascii', 'ignore').decode().strip() or "korea"
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(q)}&image_type=photo&per_page=10&safesearch=true"
        res = requests.get(url, timeout=10).json()
        if res.get("hits"):
            hits = random.sample(res["hits"], min(count, len(res["hits"])))
            for h in hits: urls.append(h["webformatURL"])
    except: pass
    return urls

def upload_to_wp_media(site_url, wp_pass, img_url, keyword, idx):
    try:
        img_data = requests.get(img_url, timeout=10).content
        filename = f"seo-{keyword.replace(' ', '-')}-{idx}.jpg"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(f"{site_url}/wp-json/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=20)
        if res.status_code == 201: return res.json().get("id")
    except: pass
    return None

def build_spider_web_links(keyword, current_url, lang):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(4, len(others)))
    html = "<div style='margin-top:30px; background:#f9f9f9; padding:15px; border-left:4px solid #0066cc;'>"
    html += f"<h4>🔗 {keyword} 연관 인기 가이드</h4><ul style='list-style:none; padding-left:0;'>"
    for s in selected:
        anchor = f"✨ [{s['theme']}] {keyword} 관련 연관 분석" if lang == 'ko' else f"✨ {keyword} Extensive Industry Report"
        html += f"<li style='margin-bottom:8px;'><a href='{s['url']}/?s={requests.utils.quote(keyword)}' target='_blank' rel='noopener'>{anchor}</a></li>"
    html += "</ul></div>"
    return html

def build_related_search_links(keyword, lang):
    words = [f"{keyword} 효능", f"{keyword} 부작용", f"{keyword} 가격", f"{keyword} 추천", f"{keyword} 비교"] if lang == 'ko' else [f"{keyword} cost", f"{keyword} review", f"{keyword} comparison", f"{keyword} guide", f"best {keyword}"]
    html = "<div style='margin-top:20px; border-top:1px dashed #ccc; padding-top:15px;'>"
    html += "<strong>💡 연관 검색어 바로가기: </strong> "
    links = []
    for w in words:
        links.append(f"<a href='?s={requests.utils.quote(w)}' style='color:#555; text-decoration:underline; margin-right:10px;'>#{w}</a>")
    html += ", ".join(links) + "</div>"
    return html

def run():
    now = datetime.now()
    minute_slot = now.minute
    hour_slot = now.hour
    
    print(f"🚀 오토봇 스케줄 감지 완료 - 현재 시각: {hour_slot}시 {minute_slot}분")
    
    if minute_slot in [0, 30]:
        site = SITES_CONFIG[0]
        wp_pass = os.getenv(site['wp_pass_env'])
        if wp_pass:
            keyword = load_keyword(site['keywords_file'], "체지방 감소 식품")
            prompt = make_seo_prompt(keyword, site['theme'], site['lang'], "blog")
            res = gemini_client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
            article = res.text if res.text else ""
            
            if len(article) > 300:
                article += build_spider_web_links(keyword, site['url'], 'ko')
                article += build_related_search_links(keyword, 'ko')
                img_urls = get_multiple_images(keyword, 3)
                media_ids = []
                for idx, url in enumerate(img_urls):
                    mid = upload_to_wp_media(site['url'], wp_pass, url, keyword, idx)
                    if mid: media_ids.append(mid)
                
                payload = {
                    "title": f"{keyword} 정보 완벽 정리",
                    "content": article,
                    "categories": [random.choice(HEALTH_CATEGORIES)],
                    "status": "publish"
                }
                if media_ids: payload["featured_media"] = media_ids[0]
                
                requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload, auth=(WP_USER, wp_pass), timeout=20)
                print(f"✅ 메인허브 분산 카테고리 발행 성공")

    # 신문사 포스팅 파트 환경 변수 연동 수정 완료
    if hour_slot % 2 == 0 and minute_slot == 15:
        site = SITES_CONFIG[1]
        wp_pass = os.getenv(site['wp_pass_env']) # KOREANEWS365COM 값을 정확하게 수집함
            
        if wp_pass:
            ref_title, ref_desc = crawl_rss_news()
            prompt = make_seo_prompt(ref_title, site['theme'], 'ko', "news")
            res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            article = res.text if res.text else ""
            
            if len(article) > 300:
                payload = {"title": f"[속보] {ref_title}", "content": article, "categories": [1], "status": "publish"}
                res_post = requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload, auth=(WP_USER, wp_pass), timeout=20)
                print(f"📰 신문사 스타일 크롤링 기반 기사 포스팅 상태코드: {res_post.status_code}")
        else:
            print(f"⚠️ 경고: {site['wp_pass_env']} 비밀번호(Secret)를 코드에서 로드할 수 없습니다.")

    global_site_idx = (hour_slot * 2 + (1 if minute_slot >= 30 else 0)) % (len(SITES_CONFIG) - 2) + 2
    site = SITES_CONFIG[global_site_idx]
    wp_pass = os.getenv(site['wp_pass_env'])
    
    if wp_pass:
        keyword = load_keyword(site['keywords_file'], site['theme'])
        prompt = make_seo_prompt(keyword, site['theme'], site['lang'], "blog")
        res = gemini_client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
        article = res.text if res.text else ""
        
        if len(article) > 300:
            article += build_spider_web_links(keyword, site['url'], site['lang'])
            article += build_related_search_links(keyword, site['lang'])
            img_urls = get_multiple_images(keyword, 4)
            media_ids = []
            for idx, url in enumerate(img_urls):
                mid = upload_to_wp_media(site['url'], wp_pass, url, keyword, idx)
                if mid: media_ids.append(mid)
            
            payload = {"title": f"The Essential Guide to {keyword}", "content": article, "categories": [1], "status": "publish"}
            if media_ids: payload["featured_media"] = media_ids[0]
            
            requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload, auth=(WP_USER, wp_pass), timeout=20)
            print(f"🌐 글로벌 사이트 [{site['url']}] 정밀 포스팅 완료")

if __name__ == "__main__":
    run()
