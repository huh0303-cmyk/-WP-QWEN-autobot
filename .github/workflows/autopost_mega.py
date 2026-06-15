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

# 외부 권위 링크 (언어별)
EXTERNAL_LINKS_KO = [
    ("https://www.who.int/ko", "세계보건기구(WHO)"),
    ("https://pubmed.ncbi.nlm.nih.gov", "PubMed 의학 논문"),
    ("https://www.mfds.go.kr", "식품의약품안전처"),
    ("https://www.mohw.go.kr", "보건복지부"),
    ("https://www.nhs.uk", "영국 NHS 건강 정보"),
    ("https://www.cdc.gov", "미국 질병통제예방센터(CDC)"),
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
        base_tags = [
            keyword,
            f"{keyword} 효능",
            f"{keyword} 방법",
            f"{keyword} 추천",
            f"{keyword} 주의사항",
            f"{keyword} {year}",
            f"{keyword} 전문가",
            theme,
            "건강정보",
            "전문가추천",
            "한국정보",
            "생활건강",
            "건강가이드",
        ]
    else:
        base_tags = [
            keyword,
            f"{keyword} guide",
            f"{keyword} tips",
            f"{keyword} {year}",
            f"best {keyword}",
            f"{keyword} expert",
            f"{keyword} review",
            theme,
            "Korea",
            "expert tips",
            "health guide",
            "lifestyle",
            "Korea info",
        ]
    return base_tags[:13]

def get_or_create_tag(site_url, wp_pass, tag_name):
    try:
        res = requests.get(
            f"{site_url}/wp-json/wp/v2/tags",
            params={"search": tag_name, "per_page": 1},
            auth=(WP_USER, wp_pass),
            timeout=10
        )
        if res.status_code == 200 and res.json():
            return res.json()[0]["id"]
        res = requests.post(
            f"{site_url}/wp-json/wp/v2/tags",
            json={"name": tag_name},
            auth=(WP_USER, wp_pass),
            timeout=10
        )
        if res.status_code == 201:
            return res.json()["id"]
    except Exception as e:
        print(f"⚠️ 태그 처리 실패 ({tag_name}): {e}")
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
    print(f"🏷️ 태그 {len(tag_ids)}개 등록: {', '.join(tags[:len(tag_ids)])}")
    return tag_ids

def build_internal_links(keyword, current_url, lang):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(10, len(others)))
    links_html = ""
    for site in selected:
        if lang == "ko":
            anchor = f"{keyword} 관련 {site['theme']} 정보"
        else:
            anchor = f"{keyword} - {site['theme']} Guide"
        links_html += f'<li><a href="{site["url"]}/?s={requests.utils.quote(keyword)}" target="_blank" rel="noopener noreferrer">{anchor}</a></li>\n'
    return links_html

def build_external_links(lang):
    ext_pool = EXTERNAL_LINKS_KO if lang == "ko" else EXTERNAL_LINKS_EN
    selected = random.sample(ext_pool, k=min(5, len(ext_pool)))
    links_html = ""
    for url, name in selected:
        links_html += f'<li><a href="{url}" target="_blank" rel="nofollow noopener noreferrer">{name}</a></li>\n'
    return links_html

def inject_links_section(content, keyword, current_url, lang):
    internal_html = build_internal_links(keyword, current_url, lang)
    external_html = build_external_links(lang)

    if lang == "ko":
        section = (
            f"\n\n<hr style='border:dashed 1px #e0e0e0;margin:40px 0;'>\n"
            f"<div style='background:#f0f7ff;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#0066cc;'>🔗 관련 추천 사이트 (내부 링크)</h3>\n"
            f"<ul style='list-style:square;padding-left:20px;'>\n"
            f"{internal_html}"
            f"</ul>\n"
            f"</div>\n"
            f"<div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#333;'>📚 참고 자료 및 외부 링크</h3>\n"
            f"<ul style='list-style:disc;padding-left:20px;'>\n"
            f"{external_html}"
            f"</ul>\n"
            f"</div>\n"
        )
    else:
        section = (
            f"\n\n<hr style='border:dashed 1px #e0e0e0;margin:40px 0;'>\n"
            f"<div style='background:#f0f7ff;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#0066cc;'>🔗 Related Resources (Internal Links)</h3>\n"
            f"<ul style='list-style:square;padding-left:20px;'>\n"
            f"{internal_html}"
            f"</ul>\n"
            f"</div>\n"
            f"<div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:20px 0;'>\n"
            f"<h3 style='color:#333;'>📚 References & External Resources</h3>\n"
            f"<ul style='list-style:disc;padding-left:20px;'>\n"
            f"{external_html}"
            f"</ul>\n"
            f"</div>\n"
        )
    return content + section

def make_prompt(keyword, theme, lang):
    if lang == "ko":
        return (
            f"당신은 15년 경력의 전문 SEO 콘텐츠 작가입니다.\n"
            f"'{keyword}'({theme}) 주제로 SEO 최적화된 전문적인 한국어 블로그 포스트를 작성하세요.\n\n"
            f"절대 필수 요건:\n"
            f"- 반드시 3000자 이상 작성 (매우 중요)\n"
            f"- HTML 태그만 사용: h2, h3, p, ul, li, ol, strong, em\n"
            f"- 마크다운 절대 금지, 별표(*) 절대 금지\n"
            f"- 첫 문단에 '{keyword}' 반드시 포함\n"
            f"- '{keyword}'를 전체 글에 10회 이상 자연스럽게 사용\n"
            f"- h2 섹션 최소 6개\n"
            f"- h3 소제목 최소 6개\n"
            f"- ul/li 목록 최소 4개 섹션\n"
            f"- 전문적이고 신뢰감 있는 의학/전문가 문체\n"
            f"- FAQ 섹션 필수 포함 (Q&A 5개 이상)\n"
            f"- 결론 섹션 포함\n"
            f"- 통계, 수치, 연구결과 등 구체적 정보 포함\n"
            f"- 독자에게 실질적으로 도움이 되는 실용 정보 위주\n"
        )
    else:
        return (
            f"You are a professional SEO content writer with 15+ years of experience.\n"
            f"Write a comprehensive, expert-level SEO-optimized blog post about '{keyword}' ({theme}) in English.\n\n"
            f"ABSOLUTE REQUIREMENTS:\n"
            f"- MINIMUM 3000 words (critical requirement)\n"
            f"- HTML tags ONLY: h2, h3, p, ul, li, ol, strong, em\n"
            f"- ZERO markdown, ZERO asterisks, HTML ONLY\n"
            f"- Include '{keyword}' in the very first paragraph\n"
            f"- Use '{keyword}' naturally 10+ times throughout\n"
            f"- Minimum 6 h2 main sections\n"
            f"- Minimum 6 h3 subsections\n"
            f"- Minimum 4 ul/li list sections\n"
            f"- Expert, authoritative, professional tone\n"
            f"- FAQ section with 5+ Q&A pairs\n"
            f"- Conclusion section\n"
            f"- Include statistics, research data, specific numbers\n"
            f"- Practical, actionable information for readers\n"
        )

def generate_article(prompt):
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            timeout=90
        )
        content = res.choices[0].message.content
        if content and len(content) > 1000:
            print("✅ Groq 생성 성공")
            return content, "Groq(llama-3.3-70b)"
    except Exception as e:
        print(f"⚠️ Groq 실패: {e}")

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 1000:
            print("✅ Gemini 2.5 Flash 생성 성공")
            return res.text, "Gemini-2.5-Flash"
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Flash 실패: {e}")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 1000:
            print("✅ Gemini 1.5 Flash 생성 성공")
            return res.text, "Gemini-1.5-Flash"
    except Exception as e:
        print(f"⚠️ Gemini 1.5 Flash 실패: {e}")

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

def publish(site, title, content, tag_ids, media_id=None):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        return False, "", f"Secret 없음: {site['wp_pass_env']}"
    payload = {
        "title":      title,
        "content":    content,
        "categories": [1],
        "tags":       tag_ids,
        "status":     "publish"
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

def run():
    total = len(SITES_CONFIG)
    print(f"🚀 총 {total}개 사이트 × 3포스트 = {total*3}개 발행 시작!")
    print(f"⏰ 시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
                article = f"<h2>{keyword} 가이드</h2><p>{keyword}에 대한 전문 정보입니다.</p>"

            seo = calc_seo_score(article, keyword)
            char_count = len(article)
            print(f"📊 SEO: {seo}/100 | 글자수: {char_count}")

            retry = 0
            while seo < 90 and retry < 3:
                retry += 1
                print(f"🔄 재작성 {retry}회차 (SEO {seo}점)")
                new_article, new_engine = generate_article(prompt)
                if new_article and len(new_article) > len(article):
                    article = new_article
                    engine = new_engine
                    seo = calc_seo_score(article, keyword)
                    char_count = len(article)
                    print(f"📊 재작성 후 SEO: {seo}/100 | 글자수: {char_count}")

            if seo >= 90:
                print(f"🎯 SEO {seo}점 달성!")
            elif seo >= 80:
                print(f"🟡 SEO {seo}점 → 발행")
            else:
                print(f"⚠️ SEO {seo}점 → 그냥 발행")

            # 내부10개 + 외부5개 링크 삽입
            final = inject_links_section(article, keyword, site['url'], lang)

            # 태그 13개 생성
            tag_ids = create_tag_ids(site, keyword, site['theme'], lang)

            # 이미지
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

            # 발행
            success, post_url, error_msg = publish(site, title, final, tag_ids, media_id)

            elapsed = (datetime.now() - start_time).seconds
            print(f"⏱️ 소요시간: {elapsed}초")

            # 구글 시트 기록
            log_to_sheets(
                site['url'], keyword, title,
                engine, image_count, image_source,
                char_count, seo, success,
                post_url, error_msg
            )

            if not (i == total and post_num == 3):
                print(f"⏳ 3분 대기...")
                time.sleep(180)

    print(f"\n🏁 전체 완료! 종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 가동")
    run()
    sys.exit(0)
