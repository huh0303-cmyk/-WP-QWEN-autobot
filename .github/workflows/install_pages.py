#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_pages.py — 27개 사이트 필수 페이지 일괄 설치
개인정보처리방침 / 면책공고 / 문의하기 / 사이트소개
GitHub Actions 또는 로컬 실행 모두 가능
"""

import os, sys, time, json
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
WP_USER = "huh0303@gmail.com"

# ============================================================
# 27개 사이트 설정
# ============================================================
SITES_CONFIG = [
    {"url": "https://k-health365.com",        "lang": "ko", "name": "K-Health 365",               "wp_pass_env": "KHEALTH365COM"},
    {"url": "https://koreamedicaltour.com",    "lang": "en", "name": "Korea Medical Tour",          "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://koreainvest365.com",      "lang": "en", "name": "Korea Invest 365",            "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://ki-korea.com",            "lang": "ko", "name": "KI Korea",                    "wp_pass_env": "KIKOREACOM"},
    {"url": "https://koreainsurance365.com",   "lang": "en", "name": "Korea Insurance 365",         "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://kfinance365.com",         "lang": "en", "name": "KFinance 365",                "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreataxnlaw.com",        "lang": "en", "name": "Korea Tax & Law",             "wp_pass_env": "KOREATAXNLAWCOM"},
    {"url": "https://koreacrypto365.com",      "lang": "en", "name": "Korea Crypto 365",            "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://krealestate365.com",      "lang": "ko", "name": "K Real Estate 365",           "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",            "lang": "en", "name": "KTech 365",                   "wp_pass_env": "KTECH365COM"},
    {"url": "https://kskin365.com",            "lang": "en", "name": "KSkin 365",                   "wp_pass_env": "KSKIN365COM"},
    {"url": "https://oliveyoungkorea.com",     "lang": "en", "name": "Olive Young Korea",           "wp_pass_env": "OLIVEYOUNGKOREACOM"},
    {"url": "https://kworld365.com",           "lang": "en", "name": "KWorld 365",                  "wp_pass_env": "KWORLD365COM"},
    {"url": "https://k-trip365.com",           "lang": "en", "name": "K-Trip 365",                  "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",           "lang": "en", "name": "K-Visa 365",                  "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com",     "lang": "en", "name": "Korea Wedding 365",           "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://kstudy365.com",           "lang": "en", "name": "KStudy 365",                  "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",     "lang": "en", "name": "Study in Korea 365",          "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kieca-korea.org",         "lang": "ko", "name": "KIECA Korea",                 "wp_pass_env": "KIECAKOREAORG"},
    {"url": "https://ksa-korea.org",           "lang": "ko", "name": "KSA Korea",                   "wp_pass_env": "KSAKOREAORG"},
    {"url": "https://sis-korea.com",           "lang": "en", "name": "SIS Korea",                   "wp_pass_env": "SISKOREACOM"},
    {"url": "https://jobkorea365.com",         "lang": "en", "name": "Job Korea 365",               "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobinkorea365.com",       "lang": "en", "name": "Job in Korea 365",            "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",      "lang": "en", "name": "Job Korea Global",            "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://korea365.org",            "lang": "en", "name": "Korea 365",                   "wp_pass_env": "KOREA365ORG"},
    {"url": "https://koreanews365.com",        "lang": "ko", "name": "더한국타임즈",                  "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",     "lang": "en", "name": "The Seoul Journal",           "wp_pass_env": "THESEOULJOURNALCOM"},
]

# ============================================================
# 페이지 콘텐츠 (한국어)
# ============================================================
def make_pages_ko(site_name: str, site_url: str) -> list:
    domain = site_url.replace("https://", "").replace("http://", "")
    return [
        {
            "slug": "privacy-policy",
            "title": "개인정보처리방침 (Privacy Policy)",
            "keyword": "개인정보처리방침",
            "content": f"""<h2>개인정보처리방침</h2>
<p><strong>{site_name}</strong>({site_url})은 이용자의 개인정보를 중요하게 생각하며, 「개인정보 보호법」 및 관련 법령을 준수합니다.</p>

<h2>1. 수집하는 개인정보 항목</h2>
<p>본 사이트는 서비스 제공을 위해 다음과 같은 개인정보를 수집할 수 있습니다.</p>
<ul>
<li>이름, 이메일 주소 (문의 시)</li>
<li>접속 IP 주소, 쿠키, 방문 기록 (자동 수집)</li>
<li>서비스 이용 기록, 접속 로그</li>
</ul>

<h2>2. 개인정보 수집 및 이용 목적</h2>
<ul>
<li>이용자 문의 응답 및 서비스 안내</li>
<li>사이트 서비스 개선 및 통계 분석</li>
<li>법령 준수 및 분쟁 해결</li>
</ul>

<h2>3. 개인정보 보유 및 이용 기간</h2>
<p>수집된 개인정보는 수집 목적이 달성된 후 즉시 파기합니다. 단, 관련 법령에 따라 일정 기간 보관이 필요한 경우 해당 기간 동안 보관합니다.</p>

<h2>4. 제3자 제공</h2>
<p>본 사이트는 이용자의 동의 없이 개인정보를 제3자에게 제공하지 않습니다. 단, 법령에 따른 요청이 있는 경우는 예외로 합니다.</p>

<h2>5. 쿠키(Cookie) 정책</h2>
<p>본 사이트는 서비스 향상을 위해 쿠키를 사용할 수 있습니다. 브라우저 설정을 통해 쿠키 수집을 거부할 수 있으나, 일부 서비스 이용에 제한이 있을 수 있습니다.</p>

<h2>6. Google AdSense 및 광고</h2>
<p>본 사이트는 Google AdSense를 통해 광고를 게재합니다. Google은 쿠키를 사용하여 이용자의 관심사에 맞는 광고를 표시할 수 있습니다. Google의 개인정보 처리 방침은 <a href="https://policies.google.com/privacy" rel="noopener noreferrer" target="_blank">Google 개인정보처리방침</a>을 참고하세요.</p>

<h2>7. 개인정보 보호 담당자</h2>
<p>개인정보 관련 문의사항은 아래 연락처로 문의하시기 바랍니다.</p>
<ul>
<li>이메일: huh0303@gmail.com</li>
<li>사이트: <a href="{site_url}/contact">{domain} 문의 페이지</a></li>
</ul>

<h2>8. 방침 변경 안내</h2>
<p>본 개인정보처리방침은 법령 또는 사이트 정책 변경에 따라 수정될 수 있으며, 변경 시 본 페이지를 통해 공지합니다.</p>
<p><strong>시행일: 2025년 1월 1일</strong></p>"""
        },
        {
            "slug": "disclaimer",
            "title": "면책공고 (Disclaimer)",
            "keyword": "면책공고",
            "content": f"""<h2>면책공고 (Disclaimer)</h2>
<p><strong>{site_name}</strong>({site_url})에서 제공하는 모든 정보는 일반적인 참고 목적으로만 제공됩니다.</p>

<h2>1. 정보의 정확성</h2>
<p>본 사이트의 콘텐츠는 신뢰할 수 있는 출처를 바탕으로 작성되었으나, 정보의 완전성·정확성·최신성을 보장하지 않습니다. 본 사이트에 게재된 정보를 근거로 한 행동에 대해 법적 책임을 지지 않습니다.</p>

<h2>2. 전문적 조언 대체 불가</h2>
<p>본 사이트의 콘텐츠는 의료, 법률, 금융, 세무 등 전문적인 조언을 대체하지 않습니다. 개인적인 상황에 적합한 결정을 위해서는 반드시 해당 분야 전문가와 상담하시기 바랍니다.</p>
<ul>
<li><strong>의료 정보:</strong> 진단 및 치료는 반드시 의사와 상담하세요.</li>
<li><strong>금융/투자 정보:</strong> 투자는 원금 손실 위험이 있으며, 전문 금융 상담사와 상의하세요.</li>
<li><strong>법률 정보:</strong> 법적 판단은 반드시 변호사와 상담하세요.</li>
</ul>

<h2>3. 외부 링크</h2>
<p>본 사이트는 외부 웹사이트로의 링크를 포함할 수 있습니다. 외부 링크 사이트의 콘텐츠 및 개인정보 처리에 대해 본 사이트는 책임을 지지 않습니다.</p>

<h2>4. 저작권</h2>
<p>본 사이트의 모든 콘텐츠는 저작권법에 의해 보호됩니다. 사전 서면 동의 없이 콘텐츠를 무단으로 복제, 배포, 수정하는 행위를 금합니다.</p>

<h2>5. 광고 공개</h2>
<p>본 사이트는 Google AdSense 등의 광고 프로그램에 참여하여 광고 수익을 얻을 수 있습니다. 광고 콘텐츠는 본 사이트의 편집 방향과 독립적으로 운영됩니다.</p>

<p><strong>문의:</strong> huh0303@gmail.com</p>"""
        },
        {
            "slug": "contact",
            "title": "문의하기 (Contact Us)",
            "keyword": "문의하기",
            "content": f"""<h2>문의하기</h2>
<p><strong>{site_name}</strong>에 방문해 주셔서 감사합니다. 아래 채널을 통해 언제든지 문의하실 수 있습니다.</p>

<h2>연락처 정보</h2>
<ul>
<li><strong>이메일:</strong> huh0303@gmail.com</li>
<li><strong>사이트:</strong> <a href="{site_url}">{site_url}</a></li>
<li><strong>운영 시간:</strong> 월~금 09:00 ~ 18:00 KST</li>
</ul>

<h2>문의 가능한 사항</h2>
<ul>
<li>콘텐츠 오류 제보 및 수정 요청</li>
<li>광고 문의 및 협력 제안</li>
<li>저작권 관련 문의</li>
<li>개인정보 관련 요청</li>
<li>기타 사이트 관련 문의</li>
</ul>

<h2>이메일 문의 안내</h2>
<p>이메일 문의 시 아래 내용을 포함해 주시면 보다 신속하게 답변드릴 수 있습니다.</p>
<ul>
<li>문의 유형 (오류 제보 / 광고 / 기타)</li>
<li>관련 페이지 URL (해당 시)</li>
<li>문의 내용 상세 설명</li>
</ul>
<p>통상 <strong>2~3 영업일 이내</strong>에 답변드립니다.</p>

<h2>개인정보처리방침</h2>
<p>문의를 통해 제공된 개인정보는 답변 목적으로만 사용되며, 관련 법령에 따라 보호됩니다.<br>
자세한 내용은 <a href="{site_url}/privacy-policy">개인정보처리방침</a>을 참고하세요.</p>"""
        },
        {
            "slug": "about",
            "title": "사이트 소개 (About)",
            "keyword": "사이트소개",
            "content": f"""<h2>{site_name} 소개</h2>
<p><strong>{site_name}</strong>은 신뢰할 수 있는 정보를 제공하기 위해 운영되는 전문 콘텐츠 플랫폼입니다.</p>

<h2>사이트 목적</h2>
<p>본 사이트는 독자 여러분께 검증된 전문 정보를 제공하는 것을 목표로 합니다. 각 분야의 전문 지식을 바탕으로 정확하고 유익한 콘텐츠를 지속적으로 발행합니다.</p>

<h2>콘텐츠 원칙</h2>
<ul>
<li><strong>정확성:</strong> 신뢰할 수 있는 출처와 전문가 검토를 통해 정확한 정보를 제공합니다.</li>
<li><strong>독립성:</strong> 광고 수익과 편집 방향은 독립적으로 운영됩니다.</li>
<li><strong>투명성:</strong> 광고 및 협력 관계를 명확하게 공개합니다.</li>
<li><strong>최신성:</strong> 정보를 지속적으로 업데이트하여 최신 내용을 제공합니다.</li>
</ul>

<h2>운영 주체</h2>
<p>본 사이트는 한국대학진학협의회(KUAC) 베트남본부와 연계된 글로벌 교육·정보 네트워크의 일환으로 운영됩니다.</p>
<ul>
<li><strong>이메일:</strong> huh0303@gmail.com</li>
<li><strong>관련 플랫폼:</strong> <a href="https://kstudy365.com">Kstudy365.com</a></li>
</ul>

<h2>면책사항</h2>
<p>본 사이트의 정보는 참고용이며 전문적인 조언을 대체하지 않습니다. 자세한 내용은 <a href="{site_url}/disclaimer">면책공고</a>를 확인하세요.</p>

<h2>문의</h2>
<p>사이트 관련 문의는 <a href="{site_url}/contact">문의하기 페이지</a>를 이용해 주세요.</p>"""
        },
    ]


# ============================================================
# 페이지 콘텐츠 (영어)
# ============================================================
def make_pages_en(site_name: str, site_url: str) -> list:
    domain = site_url.replace("https://", "").replace("http://", "")
    return [
        {
            "slug": "privacy-policy",
            "title": "Privacy Policy",
            "keyword": "privacy policy",
            "content": f"""<h2>Privacy Policy</h2>
<p><strong>{site_name}</strong> ({site_url}) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information.</p>

<h2>1. Information We Collect</h2>
<ul>
<li><strong>Contact Information:</strong> Name and email address (when you contact us)</li>
<li><strong>Usage Data:</strong> IP address, browser type, pages visited, time spent (automatically collected)</li>
<li><strong>Cookies:</strong> Session and preference cookies for improved user experience</li>
</ul>

<h2>2. How We Use Your Information</h2>
<ul>
<li>To respond to inquiries and provide customer support</li>
<li>To improve our website content and user experience</li>
<li>To analyze traffic and usage patterns (via Google Analytics)</li>
<li>To comply with legal obligations</li>
</ul>

<h2>3. Data Retention</h2>
<p>We retain personal data only as long as necessary for the stated purposes, or as required by law. Contact form submissions are retained for up to 12 months.</p>

<h2>4. Third-Party Sharing</h2>
<p>We do not sell, trade, or transfer your personal information to third parties without your consent, except as required by law or to trusted service providers who assist our site operations.</p>

<h2>5. Cookies Policy</h2>
<p>We use cookies to enhance your browsing experience. You may disable cookies through your browser settings; however, some features may not function properly without them.</p>

<h2>6. Google AdSense & Advertising</h2>
<p>This site uses Google AdSense to display advertisements. Google may use cookies to show ads based on your interests. For more information, visit <a href="https://policies.google.com/privacy" rel="noopener noreferrer" target="_blank">Google's Privacy Policy</a>.</p>

<h2>7. Your Rights</h2>
<ul>
<li>Right to access your personal data</li>
<li>Right to request correction or deletion</li>
<li>Right to opt-out of marketing communications</li>
</ul>

<h2>8. Contact</h2>
<p>For privacy-related inquiries, contact us at: <strong>huh0303@gmail.com</strong></p>
<p><strong>Effective Date: January 1, 2025</strong></p>"""
        },
        {
            "slug": "disclaimer",
            "title": "Disclaimer",
            "keyword": "disclaimer",
            "content": f"""<h2>Disclaimer</h2>
<p>The information provided by <strong>{site_name}</strong> ({site_url}) is for general informational purposes only.</p>

<h2>1. Accuracy of Information</h2>
<p>While we strive to provide accurate and up-to-date information, we make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, or suitability of the information. Any reliance you place on such information is strictly at your own risk.</p>

<h2>2. Not Professional Advice</h2>
<p>Content on this site does not constitute professional medical, legal, financial, or tax advice. Always seek the advice of qualified professionals before making decisions based on information found on this site.</p>
<ul>
<li><strong>Medical:</strong> Consult a licensed physician for diagnosis and treatment.</li>
<li><strong>Financial/Investment:</strong> Investments carry risk. Consult a certified financial advisor.</li>
<li><strong>Legal:</strong> Consult a licensed attorney for legal advice.</li>
</ul>

<h2>3. External Links</h2>
<p>This site may contain links to external websites. We have no control over the content of those sites and accept no responsibility for them or for any loss or damage that may arise from your use of them.</p>

<h2>4. Copyright</h2>
<p>All content on this site is protected by copyright law. Unauthorized reproduction, distribution, or modification is strictly prohibited without prior written consent.</p>

<h2>5. Advertising Disclosure</h2>
<p>This site participates in advertising programs including Google AdSense. We may receive compensation for displaying ads. Advertising relationships do not influence our editorial content.</p>

<p><strong>Contact:</strong> huh0303@gmail.com</p>"""
        },
        {
            "slug": "contact",
            "title": "Contact Us",
            "keyword": "contact us",
            "content": f"""<h2>Contact Us</h2>
<p>Thank you for visiting <strong>{site_name}</strong>. We'd love to hear from you. Please reach out using the contact information below.</p>

<h2>Contact Information</h2>
<ul>
<li><strong>Email:</strong> huh0303@gmail.com</li>
<li><strong>Website:</strong> <a href="{site_url}">{site_url}</a></li>
<li><strong>Business Hours:</strong> Monday–Friday, 9:00 AM – 6:00 PM KST</li>
</ul>

<h2>What You Can Contact Us About</h2>
<ul>
<li>Content corrections or feedback</li>
<li>Advertising inquiries and partnership proposals</li>
<li>Copyright and intellectual property concerns</li>
<li>Privacy and personal data requests</li>
<li>General website inquiries</li>
</ul>

<h2>How to Reach Us</h2>
<p>When emailing us, please include the following to help us respond quickly:</p>
<ul>
<li>Type of inquiry (feedback / advertising / other)</li>
<li>Relevant page URL (if applicable)</li>
<li>Detailed description of your inquiry</li>
</ul>
<p>We typically respond within <strong>2–3 business days</strong>.</p>

<h2>Privacy Notice</h2>
<p>Information submitted through contact is used solely for responding to your inquiry and is protected in accordance with our <a href="{site_url}/privacy-policy">Privacy Policy</a>.</p>"""
        },
        {
            "slug": "about",
            "title": "About Us",
            "keyword": "about us",
            "content": f"""<h2>About {site_name}</h2>
<p><strong>{site_name}</strong> is a professional content platform dedicated to providing reliable, expert-verified information to our readers.</p>

<h2>Our Mission</h2>
<p>We aim to deliver accurate, accessible, and practical content across our specialized topics. Our editorial team is committed to maintaining high standards of quality and integrity in every article we publish.</p>

<h2>Our Content Principles</h2>
<ul>
<li><strong>Accuracy:</strong> All content is researched from credible sources and reviewed by subject matter experts.</li>
<li><strong>Independence:</strong> Our editorial content remains independent from our advertising relationships.</li>
<li><strong>Transparency:</strong> We clearly disclose advertising, sponsored content, and affiliate relationships.</li>
<li><strong>Currency:</strong> We regularly update our content to reflect the latest information and developments.</li>
</ul>

<h2>Who We Are</h2>
<p>This site is operated as part of the global education and information network affiliated with the Korean Universities Admissions Council (KUAC) Vietnam Headquarters — connecting quality information to readers worldwide.</p>
<ul>
<li><strong>Email:</strong> huh0303@gmail.com</li>
<li><strong>Network:</strong> <a href="https://kstudy365.com">Kstudy365.com</a></li>
</ul>

<h2>Disclaimer</h2>
<p>Content on this site is for informational purposes only and does not constitute professional advice. See our full <a href="{site_url}/disclaimer">Disclaimer</a> for details.</p>

<h2>Get in Touch</h2>
<p>Have questions or feedback? Visit our <a href="{site_url}/contact">Contact page</a>.</p>"""
        },
    ]


# ============================================================
# WP 페이지 존재 확인
# ============================================================
def page_exists(site_url: str, wp_pass: str, slug: str) -> int:
    """기존 페이지가 있으면 page_id 반환, 없으면 0"""
    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/pages",
            auth=(WP_USER, wp_pass),
            params={"slug": slug, "per_page": 1, "_fields": "id,slug,status"},
            timeout=10
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]["id"]
    except Exception:
        pass
    return 0


# ============================================================
# WP 페이지 생성 / 업데이트
# ============================================================
def upsert_page(site_url: str, wp_pass: str, page: dict, force_update: bool = False) -> dict:
    slug    = page["slug"]
    title   = page["title"]
    content = page["content"]
    keyword = page["keyword"]

    existing_id = page_exists(site_url, wp_pass, slug)

    payload = {
        "title":   title,
        "content": content,
        "status":  "publish",
        "slug":    slug,
        "meta": {
            "rank_math_focus_keyword": keyword,
            "rank_math_description":   f"{title} — {site_url.replace('https://','').replace('http://','')}",
        }
    }

    try:
        if existing_id and not force_update:
            return {"ok": True, "action": "skipped", "id": existing_id, "slug": slug}

        if existing_id:
            r = requests.post(
                f"{site_url}/wp-json/wp/v2/pages/{existing_id}",
                auth=(WP_USER, wp_pass),
                json=payload,
                timeout=20
            )
            action = "updated"
        else:
            r = requests.post(
                f"{site_url}/wp-json/wp/v2/pages",
                auth=(WP_USER, wp_pass),
                json=payload,
                timeout=20
            )
            action = "created"

        if r.status_code in (200, 201):
            page_id  = r.json().get("id")
            page_url = r.json().get("link", "")
            return {"ok": True, "action": action, "id": page_id, "url": page_url, "slug": slug}
        else:
            return {"ok": False, "slug": slug, "status": r.status_code, "error": r.text[:200]}

    except Exception as e:
        return {"ok": False, "slug": slug, "error": str(e)[:150]}


# ============================================================
# 사이트 접근 가능 여부 확인
# ============================================================
def is_reachable(site_url: str) -> bool:
    try:
        r = requests.head(f"{site_url}/wp-json/", timeout=8, allow_redirects=True)
        return r.status_code not in (503,)
    except Exception:
        return False


# ============================================================
# 메인 실행
# ============================================================
def main():
    force_update = os.getenv("FORCE_UPDATE", "false").lower() == "true"

    print(f"\n{'='*65}")
    print(f"🚀 필수 페이지 일괄 설치 시작")
    print(f"   강제 업데이트: {'ON' if force_update else 'OFF (기존 페이지 스킵)'}")
    print(f"   대상 사이트: {len(SITES_CONFIG)}개")
    print(f"   설치 페이지: privacy-policy / disclaimer / contact / about")
    print(f"{'='*65}\n")

    results = []
    total_created = total_updated = total_skipped = total_failed = 0

    for idx, site in enumerate(SITES_CONFIG, 1):
        site_url  = site["url"]
        site_name = site["name"]
        lang      = site["lang"]
        wp_pass   = os.getenv(site["wp_pass_env"], "")

        print(f"\n[{idx:02d}/{len(SITES_CONFIG)}] {site_url}  [{site_name}]")

        if not wp_pass:
            print(f"  ⚠️  WP 비밀번호 없음 ({site['wp_pass_env']}) → 스킵")
            results.append({"site": site_url, "status": "no_password"})
            continue

        if not is_reachable(site_url):
            print(f"  ⚠️  사이트 접근 불가 → 스킵")
            results.append({"site": site_url, "status": "unreachable"})
            continue

        pages = make_pages_ko(site_name, site_url) if lang == "ko" else make_pages_en(site_name, site_url)

        site_results = []
        for page in pages:
            res = upsert_page(site_url, wp_pass, page, force_update=force_update)
            action = res.get("action", "failed")
            slug   = res.get("slug", page["slug"])

            if res["ok"]:
                if action == "created":
                    print(f"  ✅ 생성: {slug}")
                    total_created += 1
                elif action == "updated":
                    print(f"  🔄 업데이트: {slug}")
                    total_updated += 1
                else:
                    print(f"  ⏭  스킵(기존 있음): {slug}")
                    total_skipped += 1
            else:
                print(f"  ❌ 실패: {slug} — {res.get('error','')[:80]}")
                total_failed += 1

            site_results.append(res)
            time.sleep(1.5)

        results.append({"site": site_url, "pages": site_results})
        time.sleep(2)

    # 결과 요약
    print(f"\n{'='*65}")
    print(f"✅ 완료 요약")
    print(f"   생성: {total_created}개")
    print(f"   업데이트: {total_updated}개")
    print(f"   스킵(기존 있음): {total_skipped}개")
    print(f"   실패: {total_failed}개")
    print(f"{'='*65}\n")

    # JSON 결과 저장
    with open("install_pages_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("📄 결과 저장: install_pages_result.json")


if __name__ == "__main__":
    main()
