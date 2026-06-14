import os
import sys
import time
import random
import requests
from datetime import datetime
from dotenv import load_dotenv

from openai import OpenAI
import google.generativeai as genai

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

client_qwen = OpenAI(api_key=OPENAI_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

SITES_CONFIG = [
    {"url": "https://k-health365.com", "lang": "ko", "theme": "Health and Medicine", "category_id": 1, "keywords_file": "keywords_khealth.txt", "style": "blog", "adsense": True},
    {"url": "https://koreanews365.com", "lang": "ko", "theme": "General News and Issues", "category_id": 1, "keywords_file": "keywords_koreanews.txt", "style": "news", "adsense": True},
    {"url": "https://koreamedicaltour.com", "lang": "en", "theme": "Korea Medical Tourism", "category_id": 1, "keywords_file": "keywords_medicaltour.txt", "style": "blog"},
    {"url": "https://kskin365.com", "lang": "en", "theme": "K-Beauty and Skincare", "category_id": 1, "keywords_file": "keywords_kskin.txt", "style": "blog"},
    {"url": "https://korea365.org", "lang": "en", "theme": "Korea Culture and Info", "category_id": 1, "keywords_file": "keywords_korea365.txt", "style": "blog"},
    {"url": "https://jobinkorea365.com", "lang": "en", "theme": "Jobs and Career in Korea", "category_id": 1, "keywords_file": "keywords_jobinkorea.txt", "style": "blog"},
    {"url": "https://jobkorea365.com", "lang": "en", "theme": "Employment in Korea", "category_id": 1, "keywords_file": "keywords_jobkorea365.txt", "style": "blog"},
    {"url": "https://jobkoreaglobal.com", "lang": "en", "theme": "Global Career and Recruitment", "category_id": 1, "keywords_file": "keywords_jobglobal.txt", "style": "blog"},
    {"url": "https://kstudy365.com", "lang": "en", "theme": "Study in Korea and Language", "category_id": 1, "keywords_file": "keywords_kstudy.txt", "style": "blog"},
    {"url": "https://studyinkorea.com", "lang": "en", "theme": "International Students Guide", "category_id": 1, "keywords_file": "keywords_studyin.txt", "style": "blog"},
    {"url": "https://kfinance365.com", "lang": "en", "theme": "Korean Economy and Finance", "category_id": 1, "keywords_file": "keywords_kfinance.txt", "style": "blog"},
    {"url": "https://koreainvest365.com", "lang": "en", "theme": "Stock and Investment Info", "category_id": 1, "keywords_file": "keywords_kinvest.txt", "style": "blog"},
    {"url": "https://koreataxlaw.com", "lang": "en", "theme": "Tax Regulations and Law", "category_id": 1, "keywords_file": "keywords_ktax.txt", "style": "blog"},
    {"url": "https://k-trip365.com", "lang": "en", "theme": "Korea Travel and Tourism", "category_id": 1, "keywords_file": "keywords_ktrip.txt", "style": "blog"},
    {"url": "https://k-visa365.com", "lang": "en", "theme": "Immigration and Visa Services", "category_id": 1, "keywords_file": "keywords_kvisa.txt", "style": "blog"},
    {"url": "https://koreacrypto365.com", "lang": "en", "theme": "Cryptocurrency Trends", "category_id": 1, "keywords_file": "keywords_kcrypto.txt", "style": "blog"},
    {"url": "https://koreainsurance365.com", "lang": "en", "theme": "Insurance and Risk Management", "category_id": 1, "keywords_file": "keywords_kinsurance.txt", "style": "blog"},
    {"url": "https://koreavedding365.com", "lang": "en", "theme": "Korea Wedding Industry", "category_id": 1, "keywords_file": "keywords_kwedding.txt", "style": "blog"},
    {"url": "https://ktech365.com", "lang": "en", "theme": "Korean Technology and Gadgets", "category_id": 1, "keywords_file": "keywords_ktech.txt", "style": "blog"},
    {"url": "https://kworld365.com", "lang": "en", "theme": "Korean Entertainment and K-POP", "category_id": 1, "keywords_file": "keywords_kworld.txt", "style": "blog"},
    {"url": "https://oliveyoungkorea.com", "lang": "en", "theme": "K-Beauty Product Reviews", "category_id": 1, "keywords_file": "keywords_oliveyoung.txt", "style": "blog"},
    {"url": "https://theseouljournal.com", "lang": "en", "theme": "Seoul Lifestyle and Trends", "category_id": 1, "keywords_file": "keywords_seouljournal.txt", "style": "blog"}
]

ANCHOR_TEMPLATES = {
    "ko": [
        "함께 읽으면 시너지 효과가 나는 {keyword} 관련 고급 정보",
        "최근 가이드라인에 따른 {keyword} 핵심 분석 확인하기",
        "놓치면 후회하는 {keyword} 필수 주의사항 및 꿀팁 총정리"
    ],
    "en": [
        "Highly recommended guide on {keyword} for premium insights",
        "Must-read essential breakdown regarding {keyword} and updates",
        "Deep dive analysis and useful tips about {keyword} you should know"
    ]
}

def load_keyword_from_file(filename, fallback_theme):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                keywords = [line.strip() for line in f if line.strip()]
            if keywords:
                return random.choice(keywords)
    except Exception as e:
        print(f"⚠️ 파일 {filename} 읽기 실패, 기본값 사용: {str(e)}")
    return fallback_theme

def inject_spider_web_links(html_content, current_keyword, current_url, lang):
    filtered_blogs = [site for site in SITES_CONFIG if site['url'] != current_url]
    selected_sites = random.sample(filtered_blogs, k=2) if len(filtered_blogs) >= 2 else filtered_blogs
    
    backlink_html = "\n\n\n"
    backlink_html += "<hr style='border: dashed 1px #e0e0e0; margin: 30px 0;'>\n"
    backlink_html += "<div style='background-color:#f9f9f9; padding:15px; border-radius:5px;'>\n"
    title_text = "💡 유용한 추천 연관 정보" if lang == "ko" else "💡 Recommended Insights"
    backlink_html += f"  <p style='font-weight:bold; margin-bottom:10px;'>{title_text}</p>\n"
    backlink_html += "  <ul style='list-style-type: square; padding-left: 20px;'>\n"
    
    for site in selected_sites:
        templates = ANCHOR_TEMPLATES['ko'] if lang == "ko" else ANCHOR_TEMPLATES['en']
        anchor_text = random.choice(templates).format(keyword=current_keyword)
        target_link = f"{site['url']}/?s={current_keyword}"
        backlink_html += f"    <li style='margin-bottom:8px;'><a href='{target_link}' target='_blank' rel='noopener noreferrer' style='color:#0066cc; text-decoration:underline;'>{anchor_text}</a></li>\n"
        
    backlink_html += "  </ul>\n"
    backlink_html += "</div>\n"
    return html_content + backlink_html

def generate_article(prompt, keyword, lang, theme):
    try:
        res = client_qwen.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=60
        )
        return res.choices[0].message.content
    except Exception:
        pass
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        return res.text
    except Exception:
        pass
    if lang == "ko":
        return f"<h2>{keyword}에 관한 완벽 심층 정보 안내</h2><p>{theme} 분야 최고의 전문가들이 전하는 {keyword} 분석입니다.</p>"
    else:
        return f"<h2>The Ultimate Guide to {keyword}</h2><p>This is an in-depth breakdown of {keyword} regarding {theme}.</p>"

def publish_to_wordpress(site_info, title, content):
    wp_api_url = f"{site_info['url']}/wp-json/wp/v2/posts"
    payload = {"title": title, "content": content, "categories": [site_info['category_id']], "status": "publish"}
    try:
        res = requests.post(wp_api_url, json=payload, auth=(WP_USER, WP_APP_PASSWORD), timeout=25)
        if res.status_code == 201:
            print(f"✅ 발행 성공: {site_info['url']} -> [{title}]")
            return True
        print(f"❌ {site_info['url']} 응답 실패 ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"💥 {site_info['url']} 접속 불가: {str(e)}")
    return False

def run_mega_automation():
    print(f"📝 총 {len(SITES_CONFIG)}개 블로그 대상 순회 포스팅을 시작합니다.")
    for site in SITES_CONFIG:
        keyword = load_keyword_from_file(site['keywords_file'], site['theme'])
        if site['lang'] == "ko":
            title = f"{keyword}에 관한 필수 가이드 및 주의사항 총정리" if site['style'] == "blog" else f"[속보] {keyword} 관련 최근 동향 및 핵심 쟁점 분석"
            prompt = f"전문적인 블로거/기자 성격으로 '{keyword}'({site['theme']})에 대해 3000자 이상으로 한국어로 상세하게 서술해줘. HTML 태그(h2, h3, p, ul)를 사용해 줄 것."
        else:
            title = f"The Ultimate Guide to {keyword}: What You Need to Know" if site['style'] == "blog" else f"[Breaking] Latest Updates and Trends on {keyword} Explored"
            prompt = f"Act as a professional writer/journalist and write an extensive article about '{keyword}' ({site['theme']}) in English. It must be over 800 words and structuralized with HTML tags (h2, h3, p, ul)."

        print(f"🚀 처리 중: {site['url']} (키워드: {keyword})")
        article_body = generate_article(prompt, keyword, site['lang'], site['theme'])
        final_content = inject_spider_web_links(article_body, keyword, site['url'], site['lang'])
        publish_to_wordpress(site, title, final_content)
        time.sleep(random.randint(5, 15))

if __name__ == "__main__":
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스텔스 오토봇 메가 가동")
    random_delay = random.randint(1, 45)
    print(f"💤 구글 봇 감시 회피: {random_delay}분 동안 대기 모드로 수면합니다...")
    time.sleep(random_delay * 60)
    
    pass_gate = random.choice([True, False])
    if pass_gate:
        print("🎯 [주사위 합격] 포스팅 발행 가동 승인!")
        run_mega_automation()
        sys.exit(0)
    else:
        print("💤 [주사위 미통과] 구글 패스용 스킵 턴입니다. 클린 퇴근합니다.")
        sys.exit(0)
