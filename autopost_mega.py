import os
import sys
import time
import random
import requests
from datetime import datetime
import google.generativeai as genai

# ── 환경변수 로드 ──────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

WP_USER = "huh0303@gmail.com"

# ── 사이트 설정 (3개) ──────────────────────────────────────
SITES_CONFIG = [
    {
        "url": "https://k-health365.com",
        "lang": "ko",
        "theme": "Health and Medicine",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_khealth.txt",
        "style": "blog",
        "wp_pass_env": "WP_PASS_HEALTH"
    },
    {
        "url": "https://koreanews365.com",
        "lang": "ko",
        "theme": "General News and Issues",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_koreanews.txt",
        "style": "news",
        "wp_pass_env": "WP_PASS_NEWS"
    },
    {
        "url": "https://theseouljournal.com",
        "lang": "en",
        "theme": "Seoul Lifestyle and Trends",
        "category_id": 1,
        "keywords_file": ".github/workflows/keywords_seouljournal.txt",
        "style": "blog",
        "wp_pass_env": "WP_PASS_JOURNAL"
    }
]

# ── 내부 링크 앵커 텍스트 ──────────────────────────────────
ANCHOR_TEMPLATES = {
    "ko": [
        "함께 읽으면 좋은 {keyword} 관련 정보",
        "{keyword} 핵심 분석 확인하기",
        "{keyword} 필수 주의사항 총정리"
    ],
    "en": [
        "Recommended guide on {keyword}",
        "Must-read breakdown about {keyword}",
        "Deep dive analysis on {keyword}"
    ]
}

# ── 키워드 파일 로드 ───────────────────────────────────────
def load_keyword(filename, fallback):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                keywords = [line.strip() for line in f if line.strip()]
            if keywords:
                return random.choice(keywords)
    except Exception as e:
        print(f"⚠️ 키워드 파일 읽기 실패: {e}")
    return fallback

# ── 내부 링크 주입 ─────────────────────────────────────────
def inject_links(html_content, keyword, current_url, lang):
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(2, len(others)))

    title = "💡 유용한 추천 정보" if lang == "ko" else "💡 Recommended Insights"
    html = "\n\n<hr style='border:dashed 1px #e0e0e0;margin:30px 0;'>\n"
    html += "<div style='background:#f9f9f9;padding:15px;border-radius:5px;'>\n"
    html += f"<p style='font-weight:bold;'>{title}</p><ul>\n"

    for site in selected:
        templates = ANCHOR_TEMPLATES['ko'] if lang == "ko" else ANCHOR_TEMPLATES['en']
        anchor = random.choice(templates).format(keyword=keyword)
        link = f"{site['url']}/?s={keyword}"
        html += f"<li><a href='{link}' target='_blank' rel='noopener noreferrer'>{anchor}</a></li>\n"

    html += "</ul></div>\n"
    return html_content + html

# ── Gemini 콘텐츠 생성 ────────────────────────────────────
def generate_article(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        print(f"⚠️ Gemini 생성 실패: {e}")
        return None

# ── WordPress 발행 ────────────────────────────────────────
def publish(site, title, content):
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
    try:
        res = requests.post(api_url, json=payload, auth=(WP_USER, wp_pass), timeout=30)
        if res.status_code == 201:
            print(f"✅ 발행 성공: {site['url']} [{title}]")
            return True
        print(f"❌ 실패 ({res.status_code}): {site['url']} - {res.text[:200]}")
    except Exception as e:
        print(f"💥 접속 불가: {site['url']} - {e}")
    return False

# ── 메인 실행 ─────────────────────────────────────────────
def run():
    print(f"🚀 총 {len(SITES_CONFIG)}개 사이트 포스팅 시작")
    for site in SITES_CONFIG:
        keyword = load_keyword(site['keywords_file'], site['theme'])
        print(f"📝 처리 중: {site['url']} | 키워드: {keyword}")

        if site['lang'] == "ko":
            if site['style'] == "news":
                title = f"[속보] {keyword} 최근 동향 및 핵심 쟁점 분석"
            else:
                title = f"{keyword} 완벽 가이드 및 주의사항 총정리"
            prompt = (
                f"당신은 30년 경력의 전문 블로거입니다. "
                f"'{keyword}'({site['theme']}) 주제로 3000자 이상 한국어 블로그 포스트를 작성하세요. "
                f"HTML 태그(h2, h3, p, ul, li)를 사용하고 독자에게 실용적인 정보를 제공하세요."
            )
        else:
            title = f"The Ultimate Guide to {keyword}: What You Need to Know"
            prompt = (
                f"You are a professional writer with 20 years of experience. "
                f"Write an 800+ word blog post about '{keyword}' ({site['theme']}) in English. "
                f"Use HTML tags (h2, h3, p, ul, li) and provide practical, valuable information."
            )

        article = generate_article(prompt)
        if not article:
            print(f"⚠️ 콘텐츠 생성 실패, 스킵: {site['url']}")
            continue

        final = inject_links(article, keyword, site['url'], site['lang'])
        publish(site, title, final)
        time.sleep(random.randint(10, 20))

# ── 엔트리포인트 ──────────────────────────────────────────
if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오토봇 가동")
    run()
    sys.exit(0)
