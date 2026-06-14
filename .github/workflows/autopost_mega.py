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
    {
        "url": "https://k-health365.com",
        "theme": "Health and Medicine",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_khealth.txt",
        "wp_pass_env": "WP_PASS_HEALTH"
    },
    {
        "url": "https://koreanews365.com",
        "theme": "Korea News and Current Affairs",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_koreanews.txt",
        "wp_pass_env": "WP_PASS_NEWS"
    },
    {
        "url": "https://theseouljournal.com",
        "theme": "Seoul Lifestyle and Trends",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_seouljournal.txt",
        "wp_pass_env": "WP_PASS_JOURNAL"
    }
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
    # 1순위: Groq
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

    # 2순위: Gemini 2.5 Flash
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 300:
            print("✅ Gemini 2.5 Flash 생성 성공")
            return res.text
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Flash 실패: {e}")

    # 3순위: Gemini 1.5 Flash
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 300:
            print("✅ Gemini 1.5 Flash 생성 성공")
            return res.text
    except Exception as e:
        print(f"⚠️ Gemini 1.5 Flash 실패: {e}")

    # 4순위: 내부 엔진
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
        "categories": [site['category_id']],
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
        print(f"❌ 발행 실패 ({res.status_code}): {res.text[:300]}")
    except Exception as e:
        print(f"💥 접속 불가: {e}")
    return False

def run():
    print(f"🚀 3개 사이트 × 3포스트 = 총 9개 발행 시작!")
    for site in SITES_CONFIG:
        print(f"\n{'='*55}")
        print(f"🌐 {site['url']}")
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
                f"- Keyword density: naturally use '{keyword}' 8-12 times throughout\n"
                f"- Structure: Introduction → 4-5 main sections (h2) → subsections (h3) → Conclusion\n"
                f"- Include a practical tips section with ul/li\n"
                f"- Write in an engaging, authoritative, expert tone\n"
                f"- Provide real, actionable, valuable information\n"
            )

            # 글 생성
            article = generate_article(prompt)
            if not article:
                article = (
                    f"<h2>The Complete Guide to {keyword}</h2>"
                    f"<p>Understanding {keyword} is essential in the world of {site['theme']}. "
                    f"This comprehensive guide covers everything you need to know about {keyword}.</p>"
                    f"<h2>Why {keyword} Matters</h2>"
                    f"<p>{keyword} plays a crucial role in {site['theme']}. Here is what experts say.</p>"
                    f"<h3>Key Benefits of {keyword}</h3><ul>"
                    f"<li>Improved understanding of {keyword}</li>"
                    f"<li>Practical tips for applying {keyword}</li>"
                    f"<li>Expert insights on {keyword} in {site['theme']}</li>"
                    f"<li>Up-to-date information and trends</li>"
                    f"</ul>"
                    f"<h2>How to Get Started with {keyword}</h2>"
                    f"<p>Getting started with {keyword} requires understanding the basics of {site['theme']}.</p>"
                    f"<h3>Step-by-Step Guide</h3><ol>"
                    f"<li>Research the fundamentals of {keyword}</li>"
                    f"<li>Apply best practices for {keyword}</li>"
                    f"<li>Monitor and improve your {keyword} strategy</li>"
                    f"</ol>"
                    f"<h2>Expert Tips on {keyword}</h2>"
                    f"<p>Our experts share their top tips for mastering {keyword} in {site['theme']}.</p>"
                    f"<h2>Conclusion</h2>"
                    f"<p>Mastering {keyword} is a journey. With the right approach to {site['theme']}, "
                    f"you can achieve excellent results with {keyword}.</p>"
                )

            # SEO 점수
            seo = calc_seo_score(article, keyword)
            print(f"📊 SEO 점수: {seo}/100")

            retry = 0
            while seo < 80 and retry < 2:
                retry += 1
                print(f"🔄 재작성 {retry}회차 (현재 {seo}점)")
                new_article = generate_article(prompt)
                if new_article:
                    article = new_article
                    seo = calc_seo_score(article, keyword)
                    print(f"📊 재작성 후 SEO: {seo}/100")

            if seo < 80:
                print(f"⚠️ 최종 {seo}점 → 그냥 발행")
            else:
                print(f"🎯 SEO {seo}점 → 발행 승인!")

            # 내부 링크
            final = inject_links(article, keyword, site['url'])

            # 이미지
            media_id = None
            img_url = get_image(keyword)
            if img_url:
                media_id = upload_image(site, img_url, keyword)
            else:
                print("⚠️ 이미지 없이 발행")

            # 발행
            publish(site, title, final, media_id)

            # 3분 간격
            if not (site == SITES_CONFIG[-1] and post_num == 3):
                print(f"⏳ 3분 대기 중...")
                time.sleep(180)

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 가동")
    run()
    sys.exit(0)
