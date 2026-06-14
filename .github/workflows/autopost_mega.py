import os
import sys
import time
import random
import requests
from datetime import datetime
import google.generativeai as genai
from groq import Groq

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROK_API_KEY   = os.getenv("GROK_API_KEY")
PIXABAY_KEY    = os.getenv("PIXABAY_KEY")
PEXELS_KEY     = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK")
WP_USER        = "huh0303@gmail.com"

genai.configure(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROK_API_KEY)

SITES_CONFIG = [
    {"url": "https://k-health365.com",      "lang": "ko", "theme": "건강과 의학",              "keywords_file": ".github/workflows/keywords_khealth.txt",       "wp_pass_env": "WP_PASS_HEALTH"},
    {"url": "https://koreanews365.com",      "lang": "ko", "theme": "한국 뉴스와 시사",          "keywords_file": ".github/workflows/keywords_koreanews.txt",      "wp_pass_env": "WP_PASS_NEWS"},
    {"url": "https://theseouljournal.com",   "lang": "en", "theme": "Seoul Lifestyle and Trends",     "keywords_file": ".github/workflows/keywords_seouljournal.txt",  "wp_pass_env": "WP_PASS_JOURNAL"},
    {"url": "https://koreamedicaltour.com",  "lang": "en", "theme": "Korea Medical Tourism",          "keywords_file": ".github/workflows/keywords_medicaltour.txt",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://kskin365.com",          "lang": "en", "theme": "K-Beauty and Skincare",          "keywords_file": ".github/workflows/keywords_kskin.txt",         "wp_pass_env": "KSKIN365COM"},
    {"url": "https://korea365.org",          "lang": "en", "theme": "Korea Culture and Life",         "keywords_file": ".github/workflows/keywords_korea365.txt",      "wp_pass_env": "KOREA365ORG"},
    {"url": "https://jobinkorea365.com",     "lang": "en", "theme": "Jobs and Career in Korea",       "keywords_file": ".github/workflows/keywords_jobinkorea365.txt", "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkorea365.com",       "lang": "en", "theme": "Employment in Korea",            "keywords_file": ".github/workflows/keywords_jobkorea365.txt",   "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",    "lang": "en", "theme": "Global Career and Recruitment",  "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt","wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://kstudy365.com",         "lang": "en", "theme": "Study in Korea",                 "keywords_file": ".github/workflows/keywords_kstudy365.txt",     "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea.com",      "lang": "en", "theme": "International Students in Korea","keywords_file": ".github/workflows/keywords_koreanews.txt",      "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kfinance365.com",       "lang": "en", "theme": "Korean Economy and Finance",     "keywords_file": ".github/workflows/keywords_kfinance.txt",      "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreainvest365.com",    "lang": "en", "theme": "Stock and Investment in Korea",  "keywords_file": ".github/workflows/keywords_kinvest.txt",       "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://koreataxnlaw.com",      "lang": "en", "theme": "Korea Tax and Law",              "keywords_file": ".github/workflows/keywords_ktax.txt",          "wp_pass_env": "KOREATAXNLAW365COM"},
    {"url": "https://k-trip365.com",         "lang": "en", "theme": "Korea Travel and Tourism",       "keywords_file": ".github/workflows/keywords_ktrip.txt",         "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",         "lang": "en", "theme": "Korea Visa and Immigration",     "keywords_file": ".github/workflows/keywords_kvisa.txt",         "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreacrypto365.com",    "lang": "en", "theme": "Cryptocurrency in Korea",        "keywords_file": ".github/workflows/keywords_kcrypto.txt",       "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://koreainsurance365.com", "lang": "en", "theme": "Insurance in Korea",             "keywords_file": ".github/workflows/keywords_kinsurance.txt",    "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://koreavedding365.com",   "lang": "en", "theme": "Korea Wedding Industry",         "keywords_file": ".github/workflows/keywords_kwedding.txt",      "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://ktech365.com",          "lang": "en", "theme": "Korean Technology and Gadgets",  "keywords_file": ".github/workflows/keywords_ktech.txt",         "wp_pass_env": "KTECH365COM"},
    {"url": "https://kworld365.com",         "lang": "en", "theme": "Korean Entertainment and K-POP", "keywords_file": ".github/workflows/keywords_kworld.txt",        "wp_pass_env": "KWORLD365COM"},
    {"url": "https://oliveyoungkorea.com",   "lang": "en", "theme": "K-Beauty Product Reviews",       "keywords_file": ".github/workflows/keywords_oliveyoung.txt",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
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

ANCHORS_KO = [
    "함께 읽으면 좋은 {keyword} 관련 정보",
    "{keyword} 핵심 분석 확인하기",
    "{keyword} 필수 가이드 총정리",
]

ANCHORS_EN = [
    "Highly recommended guide on {keyword}",
    "Must-read breakdown about {keyword}",
    "Deep dive analysis on {keyword}",
    "Essential tips and insights on {keyword}",
]

def log_to_sheets(site_url, keyword, title, status, seo_score, char_count, post_url, error=""):
    if not SHEETS_WEBHOOK:
        return
    try:
        domain = site_url.replace("https://", "").replace("http://", "")
        payload = {
            "datetime": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "site": domain,
            "category": "",
            "keyword": keyword,
            "title": title,
            "status": "✅ OK" if status else "❌ FAIL",
            "seo_score": str(seo_score),
            "char_count": str(char_count),
            "url": post_url,
            "error": error[:200] if error else ""
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
    if lang == "ko":
        template = random.choice(KO_TITLE_TEMPLATES)
    else:
        template = random.choice(EN_TITLE_TEMPLATES)
    return template.format(keyword=keyword, year=year)

def generate_article(prompt):
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            timeout=60
        )
        content = res.choices[0].message.content
        if content and len(content) > 300:
            print("✅ Groq 생성 성공")
            return content
    except Exception as e:
        print(f"⚠️ Groq 실패: {e}")

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 300:
            print("✅ Gemini 2.5 Flash 생성 성공")
            return res.text
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Flash 실패: {e}")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 300:
            print("✅ Gemini 1.5 Flash 생성 성공")
            return res.text
    except Exception as e:
        print(f"⚠️ Gemini 1.5 Flash 실패: {e}")

    print("⚠️ 내부 엔진 사용")
    return None

def get_image(keyword):
    try:
        q = keyword.encode('ascii', 'ignore').decode()
        if not q.strip():
            q = "korea"
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(q)}&image_type=photo&per_page=5&safesearch=true&lang=en"
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("hits"):
            hit = random.choice(data["hits"])
            print("✅ Pixabay 이미지 발견")
            return hit["webformatURL"]
    except Exception as e:
        print(f"⚠️ Pixabay 실패: {e}")

    try:
        headers = {"Authorization": PEXELS_KEY}
        url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(keyword)}&per_page=5"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("photos"):
            photo = random.choice(data["photos"])
            print("✅ Pexels 이미지 발견")
            return photo["src"]["large"]
    except Exception as e:
        print(f"⚠️ Pexels 실패: {e}")

    return None

def upload_image(site, img_url, keyword):
    try:
        img_data = requests.get(img_url, timeout=15).content
        wp_pass = os.getenv(site['wp_pass_env'])
        filename = keyword.encode('ascii', 'ignore').decode().replace(' ', '-').lower()[:40] + ".jpg"
        if not filename.replace('-','').replace('.jpg',''):
            filename = "featured-image.jpg"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "image/jpeg"
        }
        res = requests.post(
            f"{site['url']}/wp-json/wp/v2/media",
            data=img_data,
            headers=headers,
            auth=(WP_USER, wp_pass),
            timeout=30
        )
        if res.status_code == 201:
            media_id = res.json().get("id")
            print(f"✅ 이미지 업로드 성공 (ID: {media_id})")
            return media_id
    except Exception as e:
        print(f"⚠️ 이미지 업로드 실패: {e}")
    return None

def inject_links(content, keyword, current_url, lang):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(2, len(others)))
    anchors = ANCHORS_KO if lang == "ko" else ANCHORS_EN
    html = "\n\n<hr style='border:dashed 1px #e0e0e0;margin:30px 0;'>\n"
    html += "<div style='background:#f9f9f9;padding:15px;border-radius:5px;'>\n"
    label = "💡 관련 추천 정보" if lang == "ko" else "💡 Recommended Insights"
    html += f"<p style='font-weight:bold;'>{label}</p><ul>\n"
    for site in selected:
        anchor = random.choice(anchors).format(keyword=keyword)
        link = f"{site['url']}/?s={requests.utils.quote(keyword)}"
        html += f"<li><a href='{link}' target='_blank' rel='noopener noreferrer'>{anchor}</a></li>\n"
    html += "</ul></div>\n"
    return content + html

def publish(site, title, content, media_id=None):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        return False, "", f"Secret 없음: {site['wp_pass_env']}"
    payload = {
        "title": title,
        "content": content,
        "categories": [1],
        "status": "publish"
    }
    if media_id:
        payload["featured_media"] = media_id
    try:
        res = requests.post(
            f"{site['url']}/wp-json/wp/v2/posts",
            json=payload,
            auth=(WP_USER, wp_pass),
            timeout=30
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

def make_prompt(keyword, theme, lang):
    if lang == "ko":
        return (
            f"당신은 15년 경력의 전문 SEO 콘텐츠 작가입니다.\n"
            f"'{keyword}'({theme}) 주제로 SEO 최적화된 한국어 블로그 포스트를 작성하세요.\n\n"
            f"필수 요건:\n"
            f"- 최소 1500자 이상 (필수)\n"
            f"- HTML 태그만 사용: h2, h3, p, ul, li, ol, strong\n"
            f"- 마크다운 사용 금지, HTML만 사용\n"
            f"- 첫 문단에 '{keyword}' 반드시 포함\n"
            f"- '{keyword}'를 자연스럽게 8~12회 사용\n"
            f"- 구성: 도입부 → h2 섹션 4~5개 → h3 소제목 → 결론\n"
            f"- ul/li 실용적 팁 섹션 포함\n"
            f"- 전문적이고 신뢰감 있는 문체\n"
            f"- FAQ 섹션 포함 (h3 + p 형식)\n"
        )
    else:
        return (
            f"You are a professional SEO content writer with 15+ years of experience.\n"
            f"Write a comprehensive, SEO-optimized blog post about '{keyword}' ({theme}) in English.\n\n"
            f"STRICT REQUIREMENTS:\n"
            f"- Minimum 1500 words (MUST)\n"
            f"- Use HTML tags ONLY: h2, h3, p, ul, li, ol, strong\n"
            f"- NO markdown, NO asterisks, ONLY HTML\n"
            f"- Include '{keyword}' in the very first paragraph\n"
            f"- Naturally use '{keyword}' 8-12 times throughout\n"
            f"- Structure: Introduction → 4-5 main h2 sections → h3 subsections → Conclusion\n"
            f"- Include practical tips with ul/li list\n"
            f"- Include a FAQ section\n"
            f"- Engaging, authoritative, expert tone\n"
        )

def run():
    total = len(SITES_CONFIG)
    print(f"🚀 총 {total}개 사이트 × 3포스트 = {total*3}개 발행 시작!")

    for i, site in enumerate(SITES_CONFIG, 1):
        lang = site['lang']
        print(f"\n{'='*55}")
        print(f"🌐 [{i}/{total}] {site['url']} ({lang.upper()})")
        print(f"{'='*55}")

        for post_num in range(1, 4):
            keyword = load_keyword(site['keywords_file'], site['theme'])
            title = make_title(keyword, lang)
            print(f"\n📝 [{post_num}/3] 키워드: {keyword}")
            print(f"📌 제목: {title}")

            prompt = make_prompt(keyword, site['theme'], lang)
            article = generate_article(prompt)
