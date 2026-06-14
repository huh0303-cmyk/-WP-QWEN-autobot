import os
import sys
import time
import random
import requests
from datetime import datetime
import google.generativeai as genai
from groq import Groq

# ── API 설정 ──────────────────────────────────────────────
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
        "lang": "en",
        "theme": "Health and Medicine",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_khealth.txt",
        "wp_pass_env": "WP_PASS_HEALTH"
    },
    {
        "url": "https://koreanews365.com",
        "lang": "en",
        "theme": "Korea News and Current Affairs",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_koreanews.txt",
        "wp_pass_env": "WP_PASS_NEWS"
    },
    {
        "url": "https://theseouljournal.com",
        "lang": "en",
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

def generate_article(prompt, keyword, theme):
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            timeout=45
        )
        content = res.choices[0].message.content
        if content and len(content) > 200:
            print("✅ Groq 생성 성공")
            return content
    except Exception as e:
        print(f"⚠️ Groq 실패: {e}")

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 200:
            print("✅ Gemini 2.5 Flash 생성 성공")
            return res.text
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Flash 실패: {e}")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        if res.text and len(res.text) > 200:
            print("✅ Gemini 1.5 Flash 생성 성공")
            return res.text
    except Exception as e:
        print(f"⚠️ Gemini 1.5 Flash 실패: {e}")

    print("⚠️ 내부 엔진 사용")
    return f"""<h2>The Complete Guide to {keyword}</h2>
<p>Welcome to our comprehensive guide on {keyword}. This article covers everything you need to know about {theme}.</p>
<h2>Why {keyword} Matters</h2>
<p>Understanding {keyword} is essential for anyone interested in {theme}. Here we break down the key aspects.</p>
<h3>Key Benefits</h3>
<ul>
<li>Comprehensive understanding of {keyword}</li>
<li>Practical tips and expert insights</li>
<li>Up-to-date information on {theme}</li>
<li>Actionable advice you can use today</li>
</ul>
<h2>Getting Started with {keyword}</h2>
<p>Whether you are a beginner or an expert, our guide on {keyword} provides valuable information tailored to your needs in {theme}.</p>
<h3>Expert Tips</h3>
<ul>
<li>Always stay informed about the latest {keyword} developments</li>
<li>Consult trusted sources when learning about {theme}</li>
<li>Apply what you learn about {keyword} consistently</li>
</ul>
<h2>Conclusion</h2>
<p>We hope this guide on {keyword} has been helpful. Stay tuned for more expert content on {theme}.</p>"""

def get_image(keyword):
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={keyword}&image_type=photo&per_page=5&safesearch=true"
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("hits"):
            hit = random.choice(data["hits"])
            return hit["webformatURL"], hit.get("pageURL", "")
    except Exception as e:
        print(f"⚠️ Pixabay 실패: {e}")

    try:
        headers = {"Authorization": PEXELS_KEY}
        url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=5"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("photos"):
            photo = random.choice(data["photos"])
            return photo["src"]["large"], photo.get("url", "")
    except Exception as e:
        print(f"⚠️ Pexels 실패: {e}")

    return None, None

def inject_links(content, keyword, current_url):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(2, len(others)))
    html = "\n\n<hr style='border:dashed 1px #e0e0e0;margin:30px 0;'>\n"
    html += "<div style='background:#f9f9f9;padding:15px;border-radius:5px;'>\n"
    html += "<p style='font-weight:bold;'>💡 Recommended Insights</p><ul>\n"
    for site in selected:
        anchor = random.choice(ANCHORS).format(keyword=keyword)
        link = f"{site['url']}/?s={keyword}"
        html += f"<li><a href='{link}' target='_blank' rel='noopener noreferrer'>{anchor}</a></li>\n"
    html += "</ul></div>\n"
    return content + html

def upload_image_to_wp(site, img_url, keyword):
    try:
        img_data = requests.get(img_url, timeout=15).content
        wp_pass = os.getenv(site['wp_pass_env'])
        media_url = f"{site['url']}/wp-json/wp/v2/media"
        filename = f"{keyword.replace(' ', '-')}.jpg"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(media_url, data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=30)
        if res.status_code == 201:
            media_id = res.json().get("id")
            print(f"✅ 이미지 업로드 성공: media_id={media_id}")
            return media_id
    except Exception as e:
        print(f"⚠️ 이미지 업로드 실패: {e}")
    return None

def publish(site, title, content, media_id=None):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        print(f"❌ Secret 없음: {site['wp_pass_env']}")
        return False
    api_url = f"{site['url']}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "categories": [site['category_id']],
        "status": "publish"
    }
    if media_id:
        payload["featured_media"] = media_id
    try:
        res = requests.post(api_url, json=payload, auth=(WP_USER, wp_pass), timeout=30)
        if res.status_code == 201:
            print(f"✅ 발행 성공: {site['url']} [{title}]")
            return True
        print(f"❌ 발행 실패 ({res.status_code}): {site['url']} - {res.text[:300]}")
    except Exception as e:
        print(f"💥 접속 불가: {site['url']} - {e}")
    return False

def run():
    print(f"🚀 총 {len(SITES_CONFIG)}개 사이트 포스팅 시작")
    for site in SITES_CONFIG:
        for post_num in range(1, 4):
            keyword = load_keyword(site['keywords_file'], site['theme'])
            print(f"\n📝 [{site['url']}] 포스트 {post_num}/3 | 키워드: {keyword}")

            title = f"The Ultimate Guide to {keyword}: Everything You Need to Know"
            prompt = (
                f"You are a professional SEO content writer. "
                f"Write a comprehensive, SEO-optimized blog post about '{keyword}' ({site['theme']}) in English. "
                f"Requirements:\n"
                f"- Minimum 900 words\n"
                f"- Use HTML tags: h2, h3, p, ul, li\n"
                f"- Include the keyword '{keyword}' naturally throughout\n"
                f"- Provide practical, valuable information\n"
                f"- Write in an engaging, authoritative tone\n"
                f"- Include a strong introduction and conclusion"
            )

            article = generate_article(prompt, keyword, site['theme'])
            seo_score = calc_seo_score(article, keyword)
            print(f"📊 SEO 점수: {seo_score}/100")

            retry = 0
            while seo_score < 80 and retry < 2:
                retry += 1
                print(f"🔄 재작성 {retry}회차")
                article = generate_article(prompt, keyword, site['theme'])
                seo_score = calc_seo_score(article, keyword)
                print(f"📊 재작성 후 SEO 점수: {seo_score}/100")

            if seo_score < 80:
                print(f"⚠️ 최종 {seo_score}점 → 그냥 발행")

            final_content = inject_links(article, keyword, site['url'])

            media_id = None
            img_url, _ = get_image(keyword)
            if img_url:
                media_id = upload_image_to_wp(site, img_url, keyword)

            publish(site, title, final_content, media_id)

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 가동")
    run()
    sys.exit(0)
