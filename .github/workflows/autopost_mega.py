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
WP_USER        = "huh0303@gmail.com"

genai.configure(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROK_API_KEY)

SITES_CONFIG = [
    {"url": "https://k-health365.com",        "theme": "Health and Medicine",               "keywords_file": ".github/workflows/keywords_khealth.txt",      "wp_pass_env": "WP_PASS_HEALTH"},
    {"url": "https://koreanews365.com",        "theme": "Korea News and Current Affairs",    "keywords_file": ".github/workflows/keywords_koreanews.txt",     "wp_pass_env": "WP_PASS_NEWS"},
    {"url": "https://theseouljournal.com",     "theme": "Seoul Lifestyle and Trends",        "keywords_file": ".github/workflows/keywords_seouljournal.txt",  "wp_pass_env": "WP_PASS_JOURNAL"},
    {"url": "https://koreamedicaltour.com",    "theme": "Korea Medical Tourism",             "keywords_file": ".github/workflows/keywords_medicaltour.txt",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://kskin365.com",            "theme": "K-Beauty and Skincare",             "keywords_file": ".github/workflows/keywords_kskin.txt",         "wp_pass_env": "KSKIN365COM"},
    {"url": "https://korea365.org",            "theme": "Korea Culture and Life",            "keywords_file": ".github/workflows/keywords_korea365.txt",      "wp_pass_env": "KOREA365ORG"},
    {"url": "https://jobinkorea365.com",       "theme": "Jobs and Career in Korea",          "keywords_file": ".github/workflows/keywords_jobinkorea365.txt", "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkorea365.com",         "theme": "Employment in Korea",               "keywords_file": ".github/workflows/keywords_jobkorea365.txt",   "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",      "theme": "Global Career and Recruitment",     "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt","wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://kstudy365.com",           "theme": "Study in Korea",                    "keywords_file": ".github/workflows/keywords_kstudy365.txt",     "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea.com",        "theme": "International Students in Korea",   "keywords_file": ".github/workflows/keywords_koreanews.txt",     "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kfinance365.com",         "theme": "Korean Economy and Finance",        "keywords_file": ".github/workflows/keywords_kfinance.txt",      "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreainvest365.com",      "theme": "Stock and Investment in Korea",     "keywords_file": ".github/workflows/keywords_kinvest.txt",       "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://koreataxnlaw.com",        "theme": "Korea Tax and Law",                 "keywords_file": ".github/workflows/keywords_ktax.txt",          "wp_pass_env": "KOREATAXNLAW365COM"},
    {"url": "https://k-trip365.com",           "theme": "Korea Travel and Tourism",          "keywords_file": ".github/workflows/keywords_ktrip.txt",         "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",           "theme": "Korea Visa and Immigration",        "keywords_file": ".github/workflows/keywords_kvisa.txt",         "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreacrypto365.com",      "theme": "Cryptocurrency in Korea",           "keywords_file": ".github/workflows/keywords_kcrypto.txt",       "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://koreainsurance365.com",   "theme": "Insurance in Korea",                "keywords_file": ".github/workflows/keywords_kinsurance.txt",    "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://koreavedding365.com",     "theme": "Korea Wedding Industry",            "keywords_file": ".github/workflows/keywords_kwedding.txt",      "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://ktech365.com",            "theme": "Korean Technology and Gadgets",     "keywords_file": ".github/workflows/keywords_ktech.txt",         "wp_pass_env": "KTECH365COM"},
    {"url": "https://kworld365.com",           "theme": "Korean Entertainment and K-POP",   "keywords_file": ".github/workflows/keywords_kworld.txt",        "wp_pass_env": "KWORLD365COM"},
    {"url": "https://oliveyoungkorea.com",     "theme": "K-Beauty Product Reviews",         "keywords_file": ".github/workflows/keywords_oliveyoung.txt",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
]

ANCHORS = [
    "Highly recommended guide on {keyword}",
    "Must-read breakdown about {keyword}",
    "Deep dive analysis on {keyword}",
    "Essential tips and insights on {keyword}",
    "Everything you need to know about {keyword}"
]

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
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(keyword)}&image_type=photo&per_page=5&safesearch=true&lang=en"
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
        filename = keyword.replace(' ', '-').lower() + ".jpg"
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

def inject_links(content, keyword, current_url):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(2, len(others)))
    html = "\n\n<hr style='border:dashed 1px #e0e0e0;margin:30px 0;'>\n"
    html += "<div style='background:#f9f9f9;padding:15px;border-radius:5px;'>\n"
    html += "<p style='font-weight:bold;'>💡 Recommended Insights</p><ul>\n"
    for site in selected:
        anchor = random.choice(ANCHORS).format(keyword=keyword)
        link = f"{site['url']}/?s={requests.utils.quote(keyword)}"
        html += f"<li><a href='{link}' target='_blank' rel='noopener noreferrer'>{anchor}</a></li>\n"
    html += "</ul></div>\n"
    return content + html

def publish(site, title, content, media_id=None):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        print(f"❌ Secret 없음: {site['wp_pass_env']}")
        return False
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
            return True
        print(f"❌ 발행 실패 ({res.status_code}): {res.text[:200]}")
    except Exception as e:
        print(f"💥 접속 불가: {e}")
    return False

def run():
    total = len(SITES_CONFIG)
    print(f"🚀 총 {total}개 사이트 × 3포스트 = {total*3}개 발행 시작!")
    for i, site in enumerate(SITES_CONFIG, 1):
        print(f"\n{'='*55}")
        print(f"🌐 [{i}/{total}] {site['url']}")
        print(f"{'='*55}")
        for post_num in range(1, 4):
            keyword = load_keyword(site['keywords_file'], site['theme'])
            print(f"\n📝 [{post_num}/3] 키워드: {keyword}")

            title = f"The Ultimate Guide to {keyword}: Everything You Need to Know"
            prompt = (
                f"You are a professional SEO content writer with 15+ years of experience.\n"
                f"Write a comprehensive, SEO-optimized blog post about '{keyword}' ({site['theme']}) in English.\n\n"
                f"STRICT REQUIREMENTS:\n"
                f"- Minimum 1500 words (MUST)\n"
                f"- Use HTML tags ONLY: h2, h3, p, ul, li, ol, strong\n"
                f"- NO markdown, NO asterisks, ONLY HTML\n"
                f"- Include '{keyword}' in the very first paragraph\n"
                f"- Naturally use '{keyword}' 8-12 times throughout\n"
                f"- Structure: Introduction → 4-5 main h2 sections → h3 subsections → Conclusion\n"
                f"- Include practical tips with ul/li list\n"
                f"- Engaging, authoritative, expert tone\n"
            )

            article = generate_article(prompt)
            if not article:
                article = (
                    f"<h2>The Complete Guide to {keyword}</h2>"
                    f"<p>{keyword} is one of the most important topics in {site['theme']}. "
                    f"This guide covers everything you need to know about {keyword}.</p>"
                    f"<h2>Why {keyword} Matters</h2>"
                    f"<p>Understanding {keyword} is essential for success in {site['theme']}.</p>"
                    f"<h3>Key Benefits of {keyword}</h3><ul>"
                    f"<li>Deep understanding of {keyword}</li>"
                    f"<li>Practical tips for {keyword}</li>"
                    f"<li>Expert insights on {keyword}</li>"
                    f"<li>Latest trends in {keyword}</li>"
                    f"</ul>"
                    f"<h2>How to Apply {keyword}</h2>"
                    f"<p>Applying {keyword} in {site['theme']} requires a strategic approach.</p>"
                    f"<h3>Step-by-Step</h3><ol>"
                    f"<li>Research {keyword} thoroughly</li>"
                    f"<li>Apply best practices for {keyword}</li>"
                    f"<li>Monitor results and improve</li>"
                    f"</ol>"
                    f"<h2>Conclusion</h2>"
                    f"<p>Mastering {keyword} will give you a competitive edge in {site['theme']}.</p>"
                )

            seo = calc_seo_score(article, keyword)
            print(f"📊 SEO 점수: {seo}/100")

            retry = 0
            while seo < 80 and retry < 2:
                retry += 1
                print(f"🔄 재작성 {retry}회차 ({seo}점)")
                new = generate_article(prompt)
                if new:
                    article = new
                    seo = calc_seo_score(article, keyword)
                    print(f"📊 재작성 후: {seo}/100")

            if seo < 80:
                print(f"⚠️ 최종 {seo}점 → 그냥 발행")
            else:
                print(f"🎯 {seo}점 → 발행 승인!")

            final = inject_links(article, keyword, site['url'])

            media_id = None
            img_url = get_image(keyword)
            if img_url:
                media_id = upload_image(site, img_url, keyword)
            else:
                print("⚠️ 이미지 없이 발행")

            publish(site, title, final, media_id)

            if not (i == total and post_num == 3):
                print(f"⏳ 3분 대기...")
                time.sleep(180)

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 가동")
    run()
    sys.exit(0)
