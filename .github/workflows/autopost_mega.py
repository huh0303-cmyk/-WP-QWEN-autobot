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
    {"url": "https://koreacrypto365.com",    "lang": "en", "theme": "Cryptocurrency in Korea",         "keywords_file": ".github/workflows/keywords_kcrypto.txt",       "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://koreainsurance365.com", "lang": "en", "theme": "Insurance in Korea",              "keywords_file": ".github/workflows/keywords_kinsurance.txt",    "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://koreavedding365.com",   "lang": "en", "theme": "Korea Wedding Industry",          "keywords_file": ".github/workflows/keywords_kwedding.txt",      "wp_pass_env": "KOREAWEDDING365COM"},
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

def log_to_sheets(site_url, keyword, title, engine, image_count,
                  image_source, char_count, seo_score, status, post_url, error=""):
    if not SHEETS_WEBHOOK:
        return
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
        if 1 <= density <= 3:
            score += 25
        elif density > 0:
            score += 10
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
            if keywords:
                return random.choice(keywords)
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
        tags = [keyword, f"{keyword} 효능", f"{keyword} 방법", f"{keyword} 추천",
                f"{keyword} 주의사항", f"{keyword} {year}", f"{keyword} 전문가",
                theme, "건강정보", "전문가추천", "한국정보", "생활건강", "건강가이드"]
    else:
        tags = [keyword, f"{keyword} guide", f"{keyword} tips", f"{keyword} {year}",
                f"best {keyword}", f"{keyword} expert", f"{keyword} review",
                theme, "Korea", "expert tips", "health guide", "lifestyle", "Korea info"]
    return tags[:13]

def get_or_create_tag(site_url, wp_pass, tag_name):
    try:
        res = requests.get(
            f"{site_url}/wp-json/wp/v2/tags",
            params={"search": tag_name, "per_page": 1},
            auth=(WP_USER, wp_pass), timeout=10
        )
        if res.status_code == 200 and res.json():
            return res.json()[0]["id"]
        res = requests.post(
            f"{site_url}/wp-json/wp/v2/tags",
            json={"name": tag_name},
            auth=(WP_USER, wp_pass), timeout=10
        )
        if res.status_code == 201:
            return res.json()["id"]
    except Exception as e:
        print(f"⚠️ 태그 실패 ({tag_name}): {e}")
    return None

def create_tag_ids(site, keyword, theme, lang):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        return []
    tags = make_tags(keyword, theme, lang)
    tag_ids = []
    for tag in tags:
        tid = get_or_create_tag(site['url'], wp_pass, tag)
        if tid:
            tag_ids.append(tid)
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
        section = (
            f"\n\n<hr style='border:dashed 1px #e0e0e0;margin:40px 0;'>\n"
            f"<div style='background:#f0f7ff;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#0066cc;'>🔗 관련 추천 사이트</h3>\n"
            f"<ul style='list-style:square;padding-left:20px;'>\n{internal}</ul>\n</div>\n"
            f"<div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#333;'>📚 참고 자료</h3>\n"
            f"<ul style='list-style:disc;padding-left:20px;'>\n{external}</ul>\n</div>\n"
        )
    else:
        section = (
            f"\n\n<hr style='border:dashed 1px #e0e0e0;margin:40px 0;'>\n"
            f"<div style='background:#f0f7ff;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#0066cc;'>🔗 Related Resources</h3>\n"
            f"<ul style='list-style:square;padding-left:20px;'>\n{internal}</ul>\n</div>\n"
            f"<div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#333;'>📚 References</h3>\n"
            f"<ul style='list-style:disc;padding-left:20px;'>\n{external}</ul>\n</div>\n"
        )
    return content + section

def make_prompt(keyword, theme, lang):
    if lang == "ko":
        return (
            f"당신은 15년 경력의 전문 SEO 콘텐츠 작가입니다.\n"
            f"'{keyword}'({theme}) 주제로 SEO 최적화된 한국어 블로그 포스트를 작성하세요.\n\n"
            f"필수 요건:\n"
            f"- 반드시 2000자 이상\n"
            f"- HTML 태그만: h2, h3, p, ul, li, ol, strong\n"
            f"- 마크다운 금지\n"
            f"- 첫 문단에 '{keyword}' 포함\n"
            f"- '{keyword}' 10회 이상 자연스럽게 사용\n"
            f"- h2 최소 5개, h3 최소 5개\n"
            f"- ul/li 목록 최소 3개\n"
            f"- FAQ 섹션 (Q&A 5개)\n"
            f"- 결론 섹션\n"
            f"- 전문적이고 신뢰감 있는 문체\n"
        )
    else:
        return (
            f"You are a professional SEO content writer with 15+ years experience.\n"
            f"Write a comprehensive blog post about '{keyword}' ({theme}) in English.\n\n"
            f"REQUIREMENTS:\n"
            f"- MINIMUM 2000 words\n"
            f"- HTML ONLY: h2, h3, p, ul, li, ol, strong\n"
            f"- NO markdown, NO asterisks\n"
            f"- Include '{keyword}' in first paragraph\n"
            f"- Use '{keyword}' 10+ times naturally\n"
            f"- Minimum 5 h2, 5 h3 sections\n"
            f"- Minimum 3 ul/li lists\n"
            f"- FAQ section (5 Q&As)\n"
            f"- Conclusion section\n"
            f"- Expert, authoritative tone\n"
        )

def generate_article(prompt):
    # 1순위: Gemini 2.5 Flash-Lite (하루 1000회)
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=8192,
                temperature=0.7,
            )
        )
        text = response.text
        if text and len(text) > 500:
            print("✅ Gemini 2.5 Flash-Lite 생성 성공")
            return text, "Gemini-2.5-Flash-Lite"
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Flash-Lite 실패: {e}")

    # 2순위: Gemini 2.5 Flash (하루 250회)
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=8192,
                temperature=0.7,
            )
        )
        text = response.text
        if text and len(text) > 500:
            print("✅ Gemini 2.5 Flash 생성 성공")
            return text, "Gemini-2.5-Flash"
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Flash 실패: {e}")

    print("⚠️ 내부 엔진 사용")
    return None, "내부엔진"

def get_image(keyword):
    try:
        q = keyword.encode('ascii', 'ignore').decode().strip() or "korea"
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(q)}&image_type=photo&per_page=5&safesearch=true&lang=en"
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("hits"):
            print("✅ Pixabay 이미지 발견")
            return random.choice(data["hits"])["webformatURL"], "Pixabay"
    except Exception as e:
        print(f"⚠️ Pixabay 실패: {e}")
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(keyword)}&per_page=5"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("photos"):
            print("✅ Pexels 이미지 발견")
            return random.choice(data["photos"])["src"]["large"], "Pexels"
    except Exception as e:
        print(f"⚠️ Pexels 실패: {e}")
    return None, "없음"

def upload_image(site, img_url, keyword):
    try:
        img_data = requests.get(img_url, timeout=15).content
        wp_pass = os.getenv(site['wp_pass_env'])
        safe_name = keyword.encode('ascii', 'ignore').decode().replace(' ', '-').lower()[:40]
        filename = (safe_name or "featured") + ".jpg"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(
            f"{site['url']}/wp-json/wp/v2/media",
            data=img_data, headers=headers,
            auth=(WP_USER, wp_pass), timeout=30
        )
        if res.status_code == 201:
            media_id = res.json().get("id")
            print(f"✅ 이미지 업로드 성공 (ID: {media_id})")
            return media_id
    except Exception as e:
        print(f"⚠️ 이미지 업로드 실패: {e}")
    return None

def publish(site, title, content, tag_ids, media_id=None):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        return False, "", f"Secret 없음: {site['wp_pass_env']}"
    payload = {
        "title": title, "content": content,
        "categories": [1], "tags": tag_ids, "status": "publish"
    }
    if media_id:
        payload["featured_media"] = media_id
    try:
        res = requests.post(
            f"{site['url']}/wp-json/wp/v2/posts",
            json=payload, auth=(WP_USER, wp_pass), timeout=30
        )
        if res.status_code == 201:
            post_url = res.json().get("link", "")
            print(f"✅ 발행 성공! → {post_url}")
            return True, post_url, ""
        error_msg = f"{res.status_code}: {res.text[:200]}"
        print(f"❌ 발행 실패: {error_msg}")
        return False, "", error_msg
    except Exception as e:
        print(f"💥 접속 불가: {e}")
        return False, "", str(e)

def make_fallback(keyword, theme, lang):
    if lang == "ko":
        return (
            f"<h2>{keyword} 완벽 가이드</h2>"
            f"<p>{keyword}은(는) {theme} 분야의 핵심 주제입니다. {keyword}에 대해 전문가 시각으로 분석합니다.</p>"
            f"<h2>{keyword}란 무엇인가?</h2>"
            f"<p>{keyword}은(는) {theme}에서 중요한 역할을 합니다.</p>"
            f"<h3>{keyword} 주요 특징</h3><ul>"
            f"<li><strong>{keyword} 핵심 원리</strong>: 기본 이해</li>"
            f"<li><strong>{keyword} 활용법</strong>: 실생활 적용</li>"
            f"<li><strong>{keyword} 최신 정보</strong>: 2026년 업데이트</li>"
            f"<li><strong>전문가 조언</strong>: 권장 사항</li>"
            f"</ul>"
            f"<h2>{keyword} 효능과 장점</h2>"
            f"<p>{keyword}을(를) 올바르게 활용하면 다양한 이점을 얻을 수 있습니다.</p>"
            f"<h3>{keyword} 장점</h3><ul>"
            f"<li>{keyword} 전문 지식 습득</li>"
            f"<li>실용적 {keyword} 활용</li>"
            f"<li>최신 {keyword} 정보 파악</li>"
            f"</ul>"
            f"<h2>{keyword} 활용 방법</h2>"
            f"<p>{keyword}을(를) 단계별로 효과적으로 활용하세요.</p>"
            f"<h3>단계별 가이드</h3><ol>"
            f"<li>{keyword} 기본 개념 이해</li>"
            f"<li>전문가 {keyword} 조언 참고</li>"
            f"<li>꾸준한 {keyword} 실천</li>"
            f"</ol>"
            f"<h2>{keyword} 주의사항</h2>"
            f"<p>{keyword} 활용 시 주의사항을 숙지하세요.</p>"
            f"<h3>주요 주의점</h3><ul>"
            f"<li>전문가 상담 후 {keyword} 시작</li>"
            f"<li>개인차 고려한 접근</li>"
            f"<li>최신 정보 지속 확인</li>"
            f"</ul>"
            f"<h2>FAQ: {keyword} 자주 묻는 질문</h2>"
            f"<h3>Q1. {keyword}은 누구에게 필요한가요?</h3>"
            f"<p>{theme}에 관심 있는 모든 분께 도움이 됩니다.</p>"
            f"<h3>Q2. {keyword} 시작 방법은?</h3>"
            f"<p>전문가 조언을 구하고 단계적으로 시작하세요.</p>"
            f"<h3>Q3. 효과는 언제 나타나나요?</h3>"
            f"<p>개인차가 있지만 꾸준한 실천이 중요합니다.</p>"
            f"<h3>Q4. 전문가는 어떻게 찾나요?</h3>"
            f"<p>{theme} 분야 전문가에게 상담을 받으세요.</p>"
            f"<h3>Q5. 최신 정보는 어디서?</h3>"
            f"<p>신뢰할 수 있는 {theme} 전문 사이트를 참고하세요.</p>"
            f"<h2>결론</h2>"
            f"<p>{keyword}은(는) {theme}에서 매우 중요합니다. 전문가와 상담하여 최적의 방법을 찾으세요.</p>"
        )
    else:
        return (
            f"<h2>The Complete Guide to {keyword}</h2>"
            f"<p>{keyword} is a crucial topic in {theme}. This guide provides expert insights on {keyword}.</p>"
            f"<h2>What is {keyword}?</h2>"
            f"<p>{keyword} plays a vital role in {theme}.</p>"
            f"<h3>Key Features of {keyword}</h3><ul>"
            f"<li><strong>Core principles</strong>: Understanding {keyword}</li>"
            f"<li><strong>Applications</strong>: Real-world {keyword} usage</li>"
            f"<li><strong>Latest trends</strong>: {keyword} in 2026</li>"
            f"<li><strong>Expert advice</strong>: {keyword} recommendations</li>"
            f"</ul>"
            f"<h2>Why {keyword} Matters</h2>"
            f"<p>{keyword} is essential for anyone in {theme}.</p>"
            f"<h3>Benefits of {keyword}</h3><ul>"
            f"<li>Deeper understanding of {keyword}</li>"
            f"<li>Practical {keyword} skills</li>"
            f"<li>Expert-backed {keyword} strategies</li>"
            f"</ul>"
            f"<h2>How to Get Started with {keyword}</h2>"
            f"<p>Starting with {keyword} requires a clear strategy in {theme}.</p>"
            f"<h3>Step-by-Step Guide</h3><ol>"
            f"<li>Research {keyword} fundamentals</li>"
            f"<li>Consult {keyword} experts</li>"
            f"<li>Apply {keyword} consistently</li>"
            f"</ol>"
            f"<h2>Common {keyword} Mistakes</h2>"
            f"<p>Avoid these mistakes when working with {keyword}.</p>"
            f"<h3>Top Pitfalls</h3><ul>"
            f"<li>Skipping expert consultation on {keyword}</li>"
            f"<li>Ignoring individual differences in {keyword}</li>"
            f"<li>Not staying updated on {keyword}</li>"
            f"</ul>"
            f"<h2>FAQ: {keyword}</h2>"
            f"<h3>Q1. Who needs {keyword}?</h3>"
            f"<p>Anyone interested in {theme} can benefit from {keyword}.</p>"
            f"<h3>Q2. How to start with {keyword}?</h3>"
            f"<p>Research and consult experts before starting {keyword}.</p>"
            f"<h3>Q3. When to see {keyword} results?</h3>"
            f"<p>Consistency is key with {keyword}.</p>"
            f"<h3>Q4. Where to find {keyword} experts?</h3>"
            f"<p>Look for certified professionals in {theme}.</p>"
            f"<h3>Q5. Latest {keyword} updates?</h3>"
            f"<p>Follow trusted {theme} resources for {keyword} news.</p>"
            f"<h2>Conclusion</h2>"
            f"<p>Mastering {keyword} gives you an edge in {theme}. Start your {keyword} journey today.</p>"
        )

def run():
    total = len(SITES_CONFIG)
    print(f"🚀 총 {total}개 사이트 × 3포스트 = {total*3}개 발행 시작!")
    print(f"⏰ 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for i, site in enumerate(SITES_CONFIG, 1):
        lang = site['lang']
        print(f"\n{'='*55}")
        print(f"🌐 [{i}/{total}] {site['url']} ({lang.upper()})")
        print(f"{'='*55}")

        for post_num in range(1, 4):
            start_time = datetime.now()
            keyword = load_keyword(site['keywords_file'], site['theme'])
            title = make_title(keyword, lang)
            print(f"\n📝 [{post_num}/3] 키워드: {keyword}")
            print(f"📌 제목: {title}")

            prompt = make_prompt(keyword, site['theme'], lang)
            article, engine = generate_article(prompt)

            if not article:
                engine = "내부엔진"
                article = make_fallback(keyword, site['theme'], lang)

            seo = calc_seo_score(article, keyword)
            char_count = len(article)
            print(f"📊 SEO: {seo}/100 | 글자수: {char_count}")

            retry = 0
            while seo < 90 and retry < 2:
                retry += 1
                print(f"🔄 재작성 {retry}회차 (SEO {seo}점)")
                new_article, new_engine = generate_article(prompt)
                if new_article and len(new_article) > len(article):
                    article = new_article
                    engine = new_engine
                    seo = calc_seo_score(article, keyword)
                    char_count = len(article)
                    print(f"📊 재작성 후: SEO {seo}/100 | {char_count}자")

            if seo >= 90:
                print(f"🎯 SEO {seo}점 달성!")
            elif seo >= 80:
                print(f"🟡 SEO {seo}점 → 발행")
            else:
                print(f"⚠️ SEO {seo}점 → 그냥 발행")

            final = inject_links_section(article, keyword, site['url'], lang)
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
            else:
                print("⚠️ 이미지 없이 발행")

            success, post_url, error_msg = publish(site, title, final, tag_ids, media_id)
            elapsed = (datetime.now() - start_time).seconds
            print(f"⏱️ 소요: {elapsed}초")

            log_to_sheets(
                site['url'], keyword, title,
                engine, image_count, image_source,
                char_count, seo, success,
                post_url, error_msg
            )

            if not (i == total and post_num == 3):
                print(f"⏳ 3분 대기...")
                time.sleep(180)

    print(f"\n🏁 완료! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 가동")
    run()
    sys.exit(0)
