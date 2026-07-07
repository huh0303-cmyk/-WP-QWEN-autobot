#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ensure_required_pages.py
─────────────────────────────────────────────────────────────
27개 사이트 전체를 대상으로 애드센스 필수 4페이지
(About / Contact / Privacy Policy / Disclaimer)가 있는지 확인하고,
없는 것만 사이트 언어(한국어/영어)에 맞춰 새로 생성합니다.
이미 있는 페이지는 절대 건드리지 않습니다.
"""

import os, time
import requests

WP_USER = "huh0303@gmail.com"
CONTACT_EMAIL = "huh0303@gmail.com"

SITES = [
    {"url": "https://k-health365.com",        "wp_pass_env": "KHEALTH365COM",        "lang": "ko", "theme": "건강 정보"},
    {"url": "https://koreamedicaltour.com",   "wp_pass_env": "KOREAMEDICALTOURCOM",  "lang": "en", "theme": "Korea Medical Tourism"},
    {"url": "https://koreainvest365.com",     "wp_pass_env": "KOREAINVEST365COM",    "lang": "en", "theme": "Investment"},
    {"url": "https://ki-korea.com",           "wp_pass_env": "KIKOREACOM",           "lang": "en", "theme": "Korea Investment"},
    {"url": "https://koreainsurance365.com",  "wp_pass_env": "KOREAINSURANCE365COM", "lang": "en", "theme": "Insurance"},
    {"url": "https://kfinance365.com",        "wp_pass_env": "KFINANCE365COM",       "lang": "en", "theme": "Finance"},
    {"url": "https://koreataxnlaw.com",       "wp_pass_env": "KOREATAXNLAWCOM",      "lang": "en", "theme": "Tax and Law"},
    {"url": "https://koreacrypto365.com",     "wp_pass_env": "KOREACRYPTO365COM",    "lang": "en", "theme": "Crypto"},
    {"url": "https://krealestate365.com",     "wp_pass_env": "KREALESTATE365COM",    "lang": "en", "theme": "Korea Real Estate"},
    {"url": "https://ktech365.com",           "wp_pass_env": "KTECH365COM",          "lang": "en", "theme": "Technology"},
    {"url": "https://kskin365.com",           "wp_pass_env": "KSKIN365COM",          "lang": "en", "theme": "K-Beauty"},
    {"url": "https://oliveyoungkorea.com",    "wp_pass_env": "OLIVEYOUNGKOREACOM",   "lang": "en", "theme": "K-Beauty Reviews"},
    {"url": "https://kworld365.com",          "wp_pass_env": "KWORLD365COM",         "lang": "en", "theme": "K-Culture"},
    {"url": "https://k-trip365.com",          "wp_pass_env": "KTRIP365COM",          "lang": "en", "theme": "Travel"},
    {"url": "https://k-visa365.com",          "wp_pass_env": "KVISA365COM",          "lang": "en", "theme": "Visa Guide"},
    {"url": "https://koreawedding365.com",    "wp_pass_env": "KOREAWEDDING365COM",   "lang": "en", "theme": "Wedding"},
    {"url": "https://kstudy365.com",          "wp_pass_env": "KSTUDY365COM",         "lang": "en", "theme": "Study in Korea"},
    {"url": "https://studyinkorea365.com",    "wp_pass_env": "STUDYINKOREA365COM",   "lang": "en", "theme": "International Students"},
    {"url": "https://kieca-korea.org",        "wp_pass_env": "KIECAKOREAORG",        "lang": "en", "theme": "International Education Culture"},
    {"url": "https://ksa-korea.org",          "wp_pass_env": "KSAKOREAORG",          "lang": "en", "theme": "Study in Korea Info"},
    {"url": "https://sis-korea.com",          "wp_pass_env": "SISKOREACOM",          "lang": "en", "theme": "Korea Career Programs"},
    {"url": "https://jobkorea365.com",        "wp_pass_env": "JOBKOREA365COM",       "lang": "en", "theme": "Employment"},
    {"url": "https://jobinkorea365.com",      "wp_pass_env": "JOBINKOREA365COM",     "lang": "en", "theme": "Jobs in Korea"},
    {"url": "https://jobkoreaglobal.com",     "wp_pass_env": "JOBKOREAGLOBALCOM",    "lang": "en", "theme": "Recruitment"},
    {"url": "https://korea365.org",           "wp_pass_env": "KOREA365ORG",          "lang": "en", "theme": "Korea Culture"},
    {"url": "https://koreanews365.com",       "wp_pass_env": "KOREANEWS365COM",      "lang": "ko", "theme": "한국 뉴스"},
    {"url": "https://theseouljournal.com",    "wp_pass_env": "THESEOULJOURNALCOM",   "lang": "en", "theme": "Seoul Lifestyle"},
]

REQUIRED_KEYWORDS = {
    "About":      ["about", "소개"],
    "Contact":    ["contact", "문의"],
    "Privacy":    ["privacy", "개인정보"],
    "Disclaimer": ["disclaimer", "면책"],
}


def get_pages(site_url, wp_pass):
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/pages",
                         auth=(WP_USER, wp_pass),
                         params={"per_page": 100, "status": "publish", "_fields": "id,title,slug,link"},
                         timeout=20)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def find_page(pages, kws):
    for p in pages:
        t = p.get("title", {}).get("rendered", "").lower()
        s = p.get("slug", "").lower()
        if any(k in t or k in s for k in kws):
            return p.get("link")
    return None


def make_content(page_type, lang, site_url, theme, is_health):
    domain = site_url.replace("https://", "")
    if lang == "ko":
        if page_type == "About":
            return f"""<p>{domain}는 {theme} 관련 정보를 제공하는 콘텐츠 사이트입니다.</p>
<p>실용적이고 신뢰할 수 있는 정보를 전달하는 것을 목표로 하며, 공신력 있는 자료와 최신 동향을 바탕으로 콘텐츠를 작성하고 있습니다.</p>
<p>문의사항은 <a href="{site_url}/contact/">문의하기</a> 페이지를 통해 연락해주시기 바랍니다.</p>"""
        if page_type == "Contact":
            return f"""<p>{domain}에 문의사항이 있으시면 아래 이메일로 연락해주세요.</p>
<p><strong>이메일:</strong> {CONTACT_EMAIL}</p>
<p>콘텐츠 수정 요청, 협업 제안, 광고 문의 등 모두 환영합니다.</p>"""
        if page_type == "Privacy":
            extra = ("<p>본 사이트의 건강 정보는 일반적인 참고용이며, 의학적 진단이나 치료를 대체하지 않습니다. "
                     "구체적인 건강 문제는 반드시 전문의와 상담하시기 바랍니다.</p>") if is_health else ""
            return f"""<p>최종 수정일: 2026년</p>
<p>{domain}("본 사이트")는 이용자의 개인정보를 소중히 다룹니다. 본 개인정보처리방침은 본 사이트 이용 시 수집·이용되는 정보에 대해 안내합니다.</p>
<h2>수집하는 정보</h2>
<p>본 사이트는 Google Analytics 등을 통해 방문자의 브라우저 정보, 방문 페이지, 체류 시간 등 비식별 정보를 수집할 수 있습니다.</p>
<h2>Google 광고(AdSense) 및 쿠키</h2>
<p>본 사이트는 Google AdSense를 사용합니다. Google은 쿠키를 사용하여 이용자의 이전 방문 기록을 기반으로 광고를 게재할 수 있습니다.
광고 개인화를 원하지 않으시면 <a href="https://adssettings.google.com" target="_blank" rel="noopener">Google 광고 설정</a>에서 옵트아웃 하실 수 있습니다.</p>
{extra}
<h2>문의</h2>
<p>개인정보처리방침 관련 문의는 <a href="{site_url}/contact/">문의하기</a> 페이지를 통해 연락해주세요.</p>"""
        if page_type == "Disclaimer":
            extra = ("<p>본 사이트의 건강·의학 관련 콘텐츠는 정보 제공 목적으로만 작성되었으며, 전문적인 의학적 조언을 대체하지 않습니다. "
                     "건강 관련 결정을 내리기 전 반드시 전문의와 상담하시기 바랍니다.</p>") if is_health else ""
            return f"""<p>{domain}에 게시된 모든 콘텐츠는 정보 제공을 목적으로 하며, 전문적인 법률·재정·의학적 조언을 대체하지 않습니다.</p>
<p>본 사이트는 콘텐츠의 정확성을 위해 노력하지만, 정보의 완전성이나 최신성을 보장하지 않으며, 콘텐츠 이용으로 인해 발생하는 어떠한 손해에 대해서도 책임지지 않습니다.</p>
{extra}
<p>본 사이트는 제휴 링크를 포함할 수 있으며, 이를 통해 수익이 발생할 수 있습니다.</p>"""
    else:
        if page_type == "About":
            return f"""<p>{domain} is a content platform focused on {theme}.</p>
<p>Our goal is to provide practical, reliable, and up-to-date information based on credible sources
and current trends.</p>
<p>For any inquiries, please reach out via our <a href="{site_url}/contact/">Contact page</a>.</p>"""
        if page_type == "Contact":
            return f"""<p>If you have any questions or feedback about {domain}, feel free to reach out.</p>
<p><strong>Email:</strong> {CONTACT_EMAIL}</p>
<p>We welcome content correction requests, collaboration proposals, and advertising inquiries.</p>"""
        if page_type == "Privacy":
            extra = ("<p>Health-related content on this site is provided for general informational purposes only "
                     "and does not substitute professional medical advice. Please consult a licensed physician "
                     "for any specific health concerns.</p>") if is_health else ""
            return f"""<p>Last updated: 2026</p>
<p>{domain} ("we", "our", "us") respects your privacy. This Privacy Policy explains how we collect,
use, and protect information when you visit our website.</p>
<h2>Information We Collect</h2>
<p>We may collect non-personal information such as browser type, device information, pages visited,
and time spent on our site through cookies and similar technologies, primarily via Google Analytics.</p>
<h2>Google AdSense and Cookies</h2>
<p>This site uses Google AdSense. Google, as a third-party vendor, uses cookies to serve ads based on
your prior visits to this and other websites. You may opt out of personalized advertising by visiting
<a href="https://adssettings.google.com" target="_blank" rel="noopener">Google Ads Settings</a>.</p>
<h2>Google Analytics</h2>
<p>We use Google Analytics to understand how visitors interact with our site.</p>
{extra}
<h2>Contact Us</h2>
<p>If you have questions about this Privacy Policy, please contact us via our
<a href="{site_url}/contact/">Contact page</a>.</p>"""
        if page_type == "Disclaimer":
            extra = ("<p>Health and medical content on this site is for informational purposes only and does not "
                     "substitute professional medical advice, diagnosis, or treatment. Always consult a qualified "
                     "healthcare provider before making health-related decisions.</p>") if is_health else ""
            return f"""<p>All content published on {domain} is provided for informational purposes only and does
not constitute professional legal, financial, or medical advice.</p>
<p>While we strive for accuracy, we make no guarantees about the completeness or timeliness of the
information, and we are not liable for any losses arising from the use of this content.</p>
{extra}
<p>This site may contain affiliate links, through which we may earn a commission.</p>"""
    return ""


def create_page(site_url, wp_pass, title, slug, content):
    r = requests.post(f"{site_url}/wp-json/wp/v2/pages",
                      auth=(WP_USER, wp_pass),
                      json={"title": title, "slug": slug, "content": content, "status": "publish"},
                      timeout=20)
    return r.status_code, (r.json() if r.status_code in (200, 201) else r.text[:200])


def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    log("=" * 60)
    log("🔍 27개 사이트 필수 4페이지 전수 점검 + 생성")
    log("=" * 60)

    total_created, total_ok, total_error = 0, 0, 0

    for site in SITES:
        url, lang, theme = site["url"], site["lang"], site["theme"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        is_health = "health" in url

        log(f"\n🌐 {url} [{lang}]")
        if not wp_pass:
            log(f"   ⚠️ 비밀번호 없음 → 건너뜀")
            continue

        pages = get_pages(url, wp_pass)
        for page_type, kws in REQUIRED_KEYWORDS.items():
            existing = find_page(pages, kws)
            if existing:
                log(f"   ✅ {page_type}: 이미 있음 ({existing})")
                total_ok += 1
                continue

            title = {
                "About": "소개" if lang == "ko" else "About Us",
                "Contact": "문의하기" if lang == "ko" else "Contact Us",
                "Privacy": "개인정보처리방침" if lang == "ko" else "Privacy Policy",
                "Disclaimer": "면책조항" if lang == "ko" else "Disclaimer",
            }[page_type]
            slug = {
                "About": "about", "Contact": "contact",
                "Privacy": "privacy-policy", "Disclaimer": "disclaimer",
            }[page_type]
            content = make_content(page_type, lang, url, theme, is_health)

            code, result = create_page(url, wp_pass, title, slug, content)
            if code in (200, 201):
                log(f"   🆕 {page_type} 생성 완료 → {result.get('link')}")
                total_created += 1
            else:
                log(f"   ❌ {page_type} 생성 실패 ({code}): {str(result)[:150]}")
                total_error += 1
            time.sleep(0.5)

        time.sleep(0.5)

    log("\n" + "=" * 60)
    log(f"✅ 완료 — 기존 확인 {total_ok}건 | 신규 생성 {total_created}건 | 오류 {total_error}건")
    log("=" * 60)

    with open("ensure_required_pages_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
