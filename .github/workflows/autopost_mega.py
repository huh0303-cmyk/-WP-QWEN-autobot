import os
import sys
import time
import random
import requests
from datetime import datetime
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY    = os.getenv("PIXABAY_KEY")
PEXELS_KEY     = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK")
WP_USER        = "huh0303@gmail.com"

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

SITES_CONFIG = [
    {"url": "https://k-health365.com",      "lang": "ko", "theme": "건강과 의학",               "keywords_file": ".github/workflows/keywords_khealth.txt",       "wp_pass_env": "WP_PASS_HEALTH"},
    {"url": "https://koreanews365.com",      "lang": "ko", "theme": "한국 뉴스와 시사",           "keywords_file": ".github/workflows/keywords_koreanews.txt",      "wp_pass_env": "WP_PASS_NEWS"},
    {"url": "https://theseouljournal.com",   "lang": "en", "theme": "Seoul Lifestyle and Trends",      "keywords_file": ".github/workflows/keywords_seouljournal.txt",  "wp_pass_env": "THESEOULJOURNALCOM"},
    {"url": "https://koreamedicaltour.com",  "lang": "en", "theme": "Korea Medical Tourism",           "keywords_file": ".github/workflows/keywords_medicaltour.txt",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://kskin365.com",          "lang": "en", "theme": "K-Beauty and Skincare",           "keywords_file": ".github/workflows/keywords_kskin.txt",         "wp_pass_env": "KSKIN365COM"},
    {"url": "https://korea365.org",          "lang": "en", "theme": "Korea Culture and Life",          "keywords_file": ".github/workflows/keywords_korea365.txt",      "wp_pass_env": "KOREA365ORG"},
    {"url": "https://jobinkorea365.com",     "lang": "en", "theme": "Jobs and Career in Korea",        "keywords_file": ".github/workflows/keywords_jobinkorea365.txt", "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkorea365.com",       "lang": "en", "theme": "Employment in Korea",             "keywords_file": ".github/workflows/keywords_jobkorea365.txt",   "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",    "lang": "en", "theme": "Global Career and Recruitment",   "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt","wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://kstudy365.com",         "lang": "en", "theme": "Study in Korea",                  "keywords_file": ".github/workflows/keywords_kstudy365.txt",     "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea.com",      "lang": "en", "theme": "International Students in Korea", "keywords_file": ".github/workflows/keywords_koreanews.txt",      "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kfinance365.com",       "lang": "en", "theme": "Korean Economy and Finance",      "keywords_file": ".github/workflows/keywords_kfinance.txt",      "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreainvest365.com",    "lang": "en", "theme": "Stock and Investment in Korea",   "keywords_file": ".github/workflows/keywords_kinvest.txt",       "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://koreataxnlaw.com",      "lang": "en", "theme": "Korea Tax and Law",               "keywords_file": ".github/workflows/keywords_ktax.txt",          "wp_pass_env": "KOREATAXNLAW365COM"},
    {"url": "https://k-trip365.com",         "lang": "en", "theme": "Korea Travel and Tourism",        "keywords_file": ".github/workflows/keywords_ktrip.txt",         "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",         "lang": "en", "theme": "Korea Visa and Immigration",      "keywords_file": ".github/workflows/keywords_kvisa.txt",         "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreacrypto365.com",    "lang": "en", "theme": "Cryptocurrency in Korea",          "keywords_file": ".github/workflows/keywords_kcrypto.txt",       "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://koreainsurance365.com", "lang": "en", "theme": "Insurance in Korea",               "keywords_file": ".github/workflows/keywords_kinsurance.txt",    "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://koreavedding365.com",   "lang": "en", "theme": "Korea Wedding Industry",           "keywords_file": ".github/workflows/keywords_kwedding.txt",      "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://ktech365.com",          "lang": "en", "theme": "Korean Technology and Gadgets",   "keywords_file": ".github/workflows/keywords_ktech.txt",         "wp_pass_env": "KTECH365COM"},
    {"url": "https://kworld365.com",         "lang": "en", "theme": "Korean Entertainment and K-POP",  "keywords_file": ".github/workflows/keywords_kworld.txt",        "wp_pass_env": "KWORLD365COM"},
    {"url": "https://oliveyoungkorea.com",   "lang": "en", "theme": "K-Beauty Product Reviews",        "keywords_file": ".github/workflows/keywords_oliveyoung.txt",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
]

EXTERNAL_LINKS_KO = [
    ("https://www.who.int/ko", "세계보건기구(WHO)"),
    ("https://pubmed.ncbi.nlm.nih.gov", "PubMed 의학 논문"),
    ("https://www.mfds.go.kr", "식품의약품안전처"),
    ("https://www.mohw.go.kr", "보건복지부"),
    ("https://www.nhs.uk", "영국 NHS 건강 정보"),
    ("https://www.cdc.gov", "미국 CDC"),
    ("https://www.korea.kr", "대한민국 정책브리핑"),
    ("https://health.kdca.go.kr", "질병관리청"),
]

EXTERNAL_LINKS_EN = [
    ("https://www.who.int", "World Health Organization (WHO)"),
    ("https://pubmed.ncbi.nlm.nih.gov", "PubMed Medical Research"),
    ("https://www.cdc.gov", "Centers for Disease Control (CDC)"),
    ("https://www.nhs.uk", "UK National Health Service"),
    ("https://www.healthline.com", "Healthline Expert Reviews"),
    ("https://www.medicalnewstoday.com", "Medical News Today"),
    ("https://www.investopedia.com", "Investopedia Financial Guide"),
    ("https://www.immihelp.com", "Immigration Help Center"),
]

KO_TITLE_TEMPLATES = [
    "{keyword}: 전문가가 알려주는 7가지 핵심 비밀 {year}",
    "{keyword} 완벽 가이드: 꼭 알아야 할 모든 것",
    "{keyword}의 놀라운 효과: 지금 바로 확인하세요",
    "당신이 몰랐던 {keyword}의 진실 7가지",
    "{keyword} {year} 최신 총정리: 전문의 추천",
    "{keyword}: 효능부터 주의사항까지 한번에 해결",
    "왜 {keyword}인가? 전문가 심층 분석 {year}",
    "{keyword} 제대로 알기: 놓치면 후회하는 핵심 정보",
]

EN_TITLE_TEMPLATES = [
    "{keyword}: 7 Expert Secrets You Need to Know in {year}",
    "{keyword} Guide {year}: What Nobody Tells You",
    "Why {keyword} Matters: A Complete Expert Breakdown",
    "{keyword}: Top 7 Facts That Will Surprise You",
    "The Truth About {keyword}: {year} Expert Analysis",
    "{keyword} Explained: Everything You Must Know Now",
    "{keyword} {year}: Proven Tips From Industry Experts",
    "Stop Ignoring {keyword}: Here's What Experts Say",
]

# [기존 보조 함수들 유지: log_to_sheets, calc_seo_score, load_keyword, make_title, make_tags, get_or_create_tag, create_tag_ids, build_internal_links, build_external_links, inject_links_section, make_prompt, get_image, upload_image, publish, make_fallback 동일]

def log_to_sheets(site_url, keyword, title, engine, image_count, image_source, char_count, seo_score, status, post_url, error=""):
    if not SHEETS_WEBHOOK: return
    try:
        domain = site_url.replace("https://", "").replace("http://", "")
        payload = {
            "datetime":     datetime.now().strftime('%Y-%m-%d %H:%M'),
            "site":         domain,
            "keyword":      keyword,
            "title":        title,
            "engine":       engine,
            "image_count":  str(image_count),
            "image_source": image_source,
            "char_count":   str(char_count),
            "seo_score":    str(seo_score),
            "status":       "✅ OK" if status else "❌ FAIL",
            "url":          post_url,
            "error":        error[:200] if error else ""
        }
        requests.post(SHEETS_WEBHOOK, json=payload, timeout=10)
        print(f"📊 구글 시트 기록 완료")
    except Exception as e:
        print(f"⚠️ 시트 기록 실패: {e}")

def calc_seo_score(content, keyword):
    score = 0
    content_lower = content.lower()
    keyword_lower = keyword.lower()
    word_count = len(content.split())
    keyword_count = content_lower.count(keyword_lower)
    if word_count > 0:
        density = (keyword_count / word_count) * 100
        if 1 <= density <= 3: score += 25
        elif density > 0: score += 10
    if "<h2" in content: score += 15
    if "<h3" in content: score += 10
    if "<ul" in content or "<ol" in content: score += 10
    if "<p"  in content: score += 10
    if word_count >= 800:  score += 20
    elif word_count >= 500: score += 10
    if keyword_lower in content_lower[:200]: score += 10
    return min(score, 100)

def load_keyword(filename, fallback):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                keywords = [l.strip() for l in f if l.strip()]
            if keywords: return random.choice(keywords)
    except Exception as e:
        print(f"⚠️ 키워드 파일 오류: {e}")
    return fallback

def make_title(keyword, lang):
    year = datetime.now().year
    templates = KO_TITLE_TEMPLATES if lang == "ko" else EN_TITLE_TEMPLATES
    return random.choice(templates).format(keyword=keyword, year=year)

def make_tags(keyword, theme, lang):
    year = str(datetime.now().year)
    if lang == "ko":
        tags = [keyword, f"{keyword} 효능", f"{keyword} 방법", f"{keyword} 추천", f"{keyword} 주의사항", f"{keyword} {year}", f"{keyword} 전문가", theme, "건강정보", "전문가추천", "한국정보", "생활건강", "건강가이드"]
    else:
        tags = [keyword, f"{keyword} guide", f"{keyword} tips", f"{keyword} {year}", f"best {keyword}", f"{keyword} expert", f"{keyword} review", theme, "Korea", "expert tips", "health guide", "lifestyle", "Korea info"]
    return tags[:13]

def get_or_create_tag(site_url, wp_pass, tag_name):
    try:
        res = requests.get(f"{site_url}/wp-json/wp/v2/tags", params={"search": tag_name, "per_page": 1}, auth=(WP_USER, wp_pass), timeout=10)
        if res.status_code == 200 and res.json(): return res.json()[0]["id"]
        res = requests.post(f"{site_url}/wp-json/wp/v2/tags", json={"name": tag_name}, auth=(WP_USER, wp_pass), timeout=10)
        if res.status_code == 201: return res.json()["id"]
    except Exception as e:
        print(f"⚠️ 태그 실패 ({tag_name}): {e}")
    return None

def create_tag_ids(site, keyword, theme, lang):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass: return []
    tags = make_tags(keyword, theme, lang)
    tag_ids = []
    for tag in tags:
        tid = get_or_create_tag(site['url'], wp_pass, tag)
        if tid: tag_ids.append(tid)
    print(f"🏷️ 태그 {len(tag_ids)}개 등록")
    return tag_ids

def build_internal_links(keyword, current_url, lang):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(10, len(others)))
    html = ""
    for site in selected:
        anchor = f"{keyword} 관련 {site['theme']} 정보" if lang == "ko" else f"{keyword} - {site['theme']} Guide"
        html += f'<li><a href="{site["url"]}/?s={requests.utils.quote(keyword)}" target="_blank" rel="noopener noreferrer">{anchor}</a></li>\n'
    return html

def build_external_links(lang):
    pool = EXTERNAL_LINKS_KO if lang == "ko" else EXTERNAL_LINKS_EN
    selected = random.sample(pool, k=min(5, len(pool)))
    html = ""
    for url, name in selected:
        html += f'<li><a href="{url}" target="_blank" rel="nofollow noopener noreferrer">{name}</a></li>\n'
    return html

def inject_links_section(content, keyword, current_url, lang):
    internal = build_internal_links(keyword, current_url, lang)
    external = build_external_links(lang)
    if lang == "ko":
        section = (f"\n\n<hr style='border:dashed 1px #e0e0e0;margin:40px 0;'>\n<div style='background:#f0f7ff;padding:20px;border-radius:8px;margin:20px 0;'>\n<h3 style='color:#0066cc;'>🔗 관련 추천 사이트</h3>\n<ul style='list-style:square;padding-left:20px;'>\n{internal}</ul>\n</div>\n<div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:20px 0;'>\n<h3 style='color:#333;'>📚 참고 자료</h3>\n<ul style='list-style:disc;padding-left:20px;'>\n{external}</ul>\n</div>\n")
    else:
        section = (f"\n\n<hr style='border:dashed 1px #e0e0e0;margin:40px 0;'>\n<div style='background:#f0f7ff;padding:20px;border-radius:8px;margin:20px 0;'>\n<h3 style='color:#0066cc;'>🔗 Related Resources</h3>\n<ul style='list-style:square;padding-left:20px;'>\n{internal}</ul>\n</div>\n<div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:20px 0;'>\n<h3 style='color:#333;'>📚 References</h3>\n<ul style='list-style:disc;padding-left:20px;'>\n{external}</ul>\n</div>\n")
    return content + section

def make_prompt(keyword, theme, lang):
    if lang == "ko":
        if "건강" in theme or "medical" in theme.lower():
            # 의학 박사 페르소나 적용
            return (f"당신은 15년 경력의 의학 박사이자 전문 SEO 콘텐츠 작가입니다.\n'{keyword}'({theme}) 주제로 깊이 있고 신뢰감 있는 의학 전문 블로그 포스트를 한국어로 작성하세요.\n\n필수 요건:\n- 반드시 2000자 이상\n- HTML 태그만: h2, h3, p, ul, li, ol, strong\n- 마크다운 금지\n- 첫 문단에 '{keyword}' 포함\n- '{keyword}' 10회 이상 자연스럽게 사용\n- h2 최소 5개, h3 최소 5개\n- ul/li 목록 최소 3개\n- FAQ 섹션 (Q&A 5개)\n- 결론 섹션\n- 전문적인 문체\n")
        return (f"당신은 15년 경력의 전문 SEO 콘텐츠 작가입니다.\n'{keyword}'({theme}) 주제로 SEO 최적화된 한국어 블로그 포스트를 작성하세요.\n\n필수 요건:\n- 반드시 2000자 이상\n- HTML 태그만: h2, h3, p, ul, li, ol, strong\n- 마크다운 금지\n- 첫 문단에 '{keyword}' 포함\n- '{keyword}' 10회 이상 자연스럽게 사용\n- h2 최소 5개, h3 최소 5개\n- ul/li 목록 최소 3개\n- FAQ 섹션 (Q&A 5개)\n- 결론 섹션\n- 전문적이고 신뢰감 있는 문체\n")
    else:
        if "k-pop" in theme.lower() or "entertainment" in theme.lower():
            # K-POP 전문가 페르소나 적용
            return (f"You are a professional K-POP industry expert and SEO content writer with 15+ years experience.\nWrite a comprehensive blog post about '{keyword}' ({theme}) in English with deep analytical insight.\n\nREQUIREMENTS:\n- MINIMUM 2000 words\n- HTML ONLY: h2, h3, p, ul, li, ol, strong\n- NO markdown, NO asterisks\n- Include '{keyword}' in first paragraph\n- Use '{keyword}' 10+ times naturally\n- Minimum 5 h2, 5 h3 sections\n- Minimum 3 ul/li lists\n- FAQ section (5 Q&As)\n- Conclusion section\n- Authoritative tone\n")
        return (f"You are a professional SEO content writer with 15+ years experience.\nWrite a comprehensive blog post about '{keyword}' ({theme}) in English.\n\nREQUIREMENTS:\n- MINIMUM 2000 words\n- HTML ONLY: h2, h3, p, ul, li, ol, strong\n- NO markdown, NO asterisks\n- Include '{keyword}' in first paragraph\n- Use '{keyword}' 10+ times naturally\n- Minimum 5 h2, 5 h3 sections\n- Minimum 3 ul/li lists\n- FAQ section (5 Q&As)\n- Conclusion section\n- Expert, authoritative tone\n")

def generate_article(prompt):
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=8192, temperature=0.7)
        )
        if response.text and len(response.text) > 500: return response.text, "Gemini-2.5-Flash-Lite"
    except Exception as e: print(f"⚠️ Gemini 2.5 Flash-Lite 실패: {e}")
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=8192, temperature=0.7)
        )
        if response.text and len(response.text) > 500: return response.text, "Gemini-2.5-Flash"
    except Exception as e: print(f"⚠️ Gemini 2.5 Flash 실패: {e}")
    return None, "내부엔진"

def get_image(keyword):
    try:
        q = keyword.encode('ascii', 'ignore').decode().strip() or "korea"
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(q)}&image_type=photo&per_page=5&safesearch=true&lang=en"
        res = requests.get(url, timeout=10).json()
        if res.get("hits"): return random.choice(res["hits"])["webformatURL"], "Pixabay"
    except Exception as e: print(f"⚠️ Pixabay 실패: {e}")
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(keyword)}&per_page=5"
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("photos"): return random.choice(res["photos"])["src"]["large"], "Pexels"
    except Exception as e: print(f"⚠️ Pexels 실패: {e}")
    return None, "없음"

def upload_image(site, img_url, keyword):
    try:
        img_data = requests.get(img_url, timeout=15).content
        wp_pass = os.getenv(site['wp_pass_env'])
        safe_name = keyword.encode('ascii', 'ignore').decode().replace(' ', '-').lower()[:40]
        filename = (safe_name or "featured") + ".jpg"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(f"{site['url']}/wp-json/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=30)
        if res.status_code == 201: return res.json().get("id")
    except Exception as e: print(f"⚠️ 이미지 업로드 실패: {e}")
    return None

def publish(site, title, content, tag_ids, media_id=None):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass: return False, "", f"Secret 없음: {site['wp_pass_env']}"
    payload = {"title": title, "content": content, "categories": [1], "tags": tag_ids, "status": "publish"}
    if media_id: payload["featured_media"] = media_id
    try:
        res = requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload, auth=(WP_USER, wp_pass), timeout=30)
        if res.status_code == 201: return True, res.json().get("link", ""), ""
        return False, "", f"{res.status_code}: {res.text[:200]}"
    except Exception as e: return False, "", str(e)

def make_fallback(keyword, theme, lang):
    if lang == "ko":
        return f"<h2>{keyword} 완벽 가이드</h2><p>{keyword}은(는) {theme} 분야의 핵심 주제입니다.</p><h2>결론</h2><p>{keyword}은(는) {theme}에서 중요합니다.</p>"
    return f"<h2>The Complete Guide to {keyword}</h2><p>{keyword} is a crucial topic in {theme}.</p><h2>Conclusion</h2><p>Mastering {keyword} gives you an edge.</p>"


# 🚀 [핵심 스케줄러 내장형 실행 로직]
def run():
    current_hour = datetime.now().hour
    print(f"⏰ 현재 구동 시각 (서버): {current_hour}시")

    # 매 실행 시 메인 건강 블로그(k-health365)와 뉴스 블로그(koreanews365) 중 하나를 무조건 교차로 우선 타격합니다.
    target_sites = []
    if current_hour % 2 == 0:
        target_sites.append(SITES_CONFIG[0]) # K-Health (짝수 시간)
    else:
        target_sites.append(SITES_CONFIG[1]) # KoreaNews (홀수 시간)

    # 나머지 20개 영문 글로벌 인프라 사이트 중 현재 시간에 할당된 1개를 추가 선택합니다.
    # 22개 사이트이므로 Hour 인덱스 매칭을 활용해 완벽하게 순환시킵니다.
    global_index = current_hour % len(SITES_CONFIG)
    if global_index not in [0, 1]: # 중복 발송 방지
        target_sites.append(SITES_CONFIG[global_index])

    print(f"🎯 이번 회차 포스팅 타겟 사이트 개수: {len(target_sites)}개")

    for site in target_sites:
        lang = site['lang']
        print(f"\n🌐 작업 도메인: {site['url']} ({lang.upper()})")

        # 각 사이트당 과도한 폭탄 발행을 막고 딱 1개씩만 양질의 포스팅을 유도합니다.
        keyword = load_keyword(site['keywords_file'], site['theme'])
        title = make_title(keyword, lang)
        print(f"📝 키워드: {keyword} | 제목: {title}")

        prompt = make_prompt(keyword, site['theme'], lang)
        article, engine = generate_article(prompt)

        if not article:
            engine = "내부엔진"
            article = make_fallback(keyword, site['theme'], lang)

        seo = calc_seo_score(article, keyword)
        char_count = len(article)

        # SEO 점수 미달 시 딱 1회만 재검토 보정 루프 진행
        if seo < 90:
            print(f"🔄 SEO 보정 1회 진행 (현재 {seo}점)")
            new_article, new_engine = generate_article(prompt)
            if new_article and len(new_article) > len(article):
                article = new_article
                engine = new_engine
                seo = calc_seo_score(article, keyword)
                char_count = len(article)

        final_content = inject_links_section(article, keyword, site['url'], lang)
        tag_ids = create_tag_ids(site, keyword, site['theme'], lang)

        image_count = 0
        image_source = "없음"
        media_id = None
        img_url, img_source = get_image(keyword)
        if img_url:
            media_id = upload_image(site, img_url, keyword)
            if media_id:
                image_count = 1
                image_source = img_source

        success, post_url, error_msg = publish(site, title, final_content, tag_ids, media_id)
        
        log_to_sheets(
            site['url'], keyword, title, engine, image_count, 
            image_source, char_count, seo, success, post_url, error_msg
        )
        
        if len(target_sites) > 1:
            time.sleep(30) # 사이트 간 부하 분산용 짧은 휴식

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 정밀 모드 가동")
    run()
    sys.exit(0)
