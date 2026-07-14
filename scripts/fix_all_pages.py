# -*- coding: utf-8 -*-
"""
스캔 결과 문제 있는 페이지(짧음/LOREM/이메일없음)를 사이트별 맞춤 실제 콘텐츠로 교체.
- 사이트 이름은 도메인에서 추출
- 연락처는 huh0303@gmail.com으로 통일
- 최소 800자 이상, 충분히 긴 내용으로 작성
"""
import os, sys, re, json, time, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

MIN_LEN = 600
EMAIL = "huh0303@gmail.com"


def site_brand(site_url, theme):
    domain = site_url.replace("https://", "").replace("http://", "").rstrip("/")
    name = domain.split(".")[0]
    pretty = re.sub(r'(365|org|com)$', '', name)
    pretty = pretty[0].upper() + pretty[1:] if pretty else name
    return domain, pretty


def build_about(domain, pretty, theme, lang):
    if lang == "ko":
        return f"""
<h2>{pretty} 소개</h2>
<p><strong>{pretty}</strong>({domain})는 '{theme}' 분야의 실용적이고 신뢰할 수 있는 정보를 제공하는 것을 목표로 운영되는 정보 플랫폼입니다.</p>
<h2>운영 목적</h2>
<p>급변하는 정보 환경 속에서 정확하고 실질적으로 도움이 되는 콘텐츠를 찾기가 점점 어려워지고 있습니다. {pretty}는 이러한 문제를 해결하기 위해 관련 분야의 최신 동향과 실제 도움이 되는 정보를 정리하여 전달하고자 합니다.</p>
<h2>콘텐츠 원칙</h2>
<ul>
<li>공신력 있는 출처를 기반으로 한 정보 작성</li>
<li>실생활에 바로 적용 가능한 실용적인 안내 제공</li>
<li>지속적인 콘텐츠 업데이트를 통한 최신성 유지</li>
</ul>
<p>{pretty}는 앞으로도 방문자에게 더 나은 정보를 제공하기 위해 콘텐츠 품질 개선을 지속하겠습니다. 문의사항은 언제든 연락처를 통해 남겨주시기 바랍니다.</p>
"""
    else:
        return f"""
<h2>About {pretty}</h2>
<p><strong>{pretty}</strong> ({domain}) is an information platform dedicated to providing practical, reliable content in the field of {theme}.</p>
<h2>Our Mission</h2>
<p>In a fast-changing information landscape, finding accurate and genuinely useful content can be difficult. {pretty} was created to address this gap by curating up-to-date, practical information that readers can actually use.</p>
<h2>Our Content Principles</h2>
<ul>
<li>Content based on credible, well-researched sources</li>
<li>Practical guidance readers can apply immediately</li>
<li>Ongoing updates to keep information current and accurate</li>
</ul>
<p>{pretty} is committed to continuously improving the quality of our content for our readers. If you have any questions, please feel free to reach out through our contact information.</p>
"""


def build_contact(domain, pretty, lang):
    if lang == "ko":
        return f"""
<h2>문의하기</h2>
<p>{pretty} 운영팀에 궁금하신 사항, 제휴 문의, 콘텐츠 관련 의견이 있으시면 아래 연락처로 언제든 문의해 주시기 바랍니다.</p>
<h3>연락처</h3>
<ul>
<li><strong>이메일:</strong> {EMAIL}</li>
</ul>
<p>이메일 문의 시 문의 내용을 최대한 구체적으로 남겨주시면 더 정확하고 빠른 답변을 드리는 데 도움이 됩니다. 영업일 기준으로 순차적으로 답변드리고 있습니다.</p>
<p>{pretty}는 방문자 여러분의 의견을 소중히 생각하며, 더 나은 콘텐츠를 만들기 위해 여러분의 피드백을 적극 반영하고 있습니다.</p>
"""
    else:
        return f"""
<h2>Contact Us</h2>
<p>If you have any questions, partnership inquiries, or feedback about our content, please feel free to reach out to the {pretty} team using the contact information below.</p>
<h3>Contact Information</h3>
<ul>
<li><strong>Email:</strong> {EMAIL}</li>
</ul>
<p>When reaching out via email, please include as much detail as possible about your inquiry so we can respond accurately and promptly. We aim to respond to all inquiries within a few business days.</p>
<p>{pretty} values feedback from our readers and actively incorporates it to continually improve the quality of our content.</p>
"""


def build_disclaimer(pretty, lang):
    if lang == "ko":
        return f"""
<h2>면책조항 (Disclaimer)</h2>
<p><strong>{pretty}</strong>에서 제공하는 모든 정보는 일반적인 참고 목적으로 제공되며, 특정 상황에 대한 전문적인 조언을 대체하지 않습니다.</p>
<h2>1. 정보의 정확성</h2>
<p>본 사이트의 콘텐츠는 신뢰할 수 있는 출처를 바탕으로 작성되었으나, 정보의 완전성, 정확성, 최신성을 완전히 보장하지는 않습니다. 본 사이트에 게재된 정보를 근거로 한 개인의 결정이나 행동에 대해 당사는 법적 책임을 지지 않습니다.</p>
<h2>2. 전문가 상담 권장</h2>
<p>본 사이트의 콘텐츠는 법률, 금융, 의료, 세무 등 전문적인 조언을 대체하지 않습니다. 개인적인 상황에 적합한 결정을 내리기 위해서는 반드시 해당 분야의 자격을 갖춘 전문가와 상담하시기 바랍니다.</p>
<h2>3. 외부 링크</h2>
<p>본 사이트는 유용한 정보 제공을 위해 외부 사이트로 연결되는 링크를 포함할 수 있습니다. 외부 사이트의 콘텐츠에 대해서는 당사가 책임지지 않습니다.</p>
<p>문의사항은 {EMAIL}으로 연락 주시기 바랍니다.</p>
"""
    else:
        return f"""
<h2>Disclaimer</h2>
<p>All information provided by <strong>{pretty}</strong> is for general informational purposes only and does not constitute professional advice for any specific situation.</p>
<h2>1. Accuracy of Information</h2>
<p>While our content is prepared using credible sources, we do not guarantee the completeness, accuracy, or timeliness of the information provided. We are not liable for any decisions or actions taken based on content published on this site.</p>
<h2>2. Professional Consultation Recommended</h2>
<p>Content on this site does not replace professional legal, financial, medical, or tax advice. Please consult a qualified professional in the relevant field before making decisions specific to your situation.</p>
<h2>3. External Links</h2>
<p>This site may contain links to external websites for informational purposes. We are not responsible for the content of external sites.</p>
<p>For inquiries, please contact us at {EMAIL}.</p>
"""


def build_privacy(pretty, lang):
    if lang == "ko":
        return f"""
<h2>개인정보처리방침</h2>
<p><strong>{pretty}</strong>는 이용자의 개인정보를 중요하게 생각하며, 관련 법령을 준수하여 개인정보를 처리합니다.</p>
<h2>1. 수집하는 개인정보 항목</h2>
<p>본 사이트는 서비스 제공을 위해 다음과 같은 정보를 수집할 수 있습니다.</p>
<ul>
<li>문의 시 입력하는 이름, 이메일 주소</li>
<li>접속 IP 주소, 쿠키, 방문 기록 등 자동 수집 정보</li>
<li>서비스 이용 기록 및 접속 로그</li>
</ul>
<h2>2. 개인정보의 수집 및 이용 목적</h2>
<ul>
<li>이용자 문의에 대한 응답 및 서비스 안내</li>
<li>사이트 서비스 개선 및 통계 분석</li>
<li>광고 게재 및 맞춤형 서비스 제공 (Google AdSense 등)</li>
</ul>
<h2>3. 쿠키 사용</h2>
<p>본 사이트는 Google AdSense를 포함한 제3자 광고 서비스를 이용하며, 이 과정에서 쿠키가 사용될 수 있습니다. 이용자는 브라우저 설정을 통해 쿠키 저장을 거부할 수 있습니다.</p>
<h2>4. 개인정보 보유 및 파기</h2>
<p>수집된 개인정보는 목적 달성 후 지체 없이 파기하며, 법령에 따라 보존이 필요한 경우 해당 기간 동안 보관합니다.</p>
<p>개인정보 관련 문의는 {EMAIL}으로 연락 주시기 바랍니다.</p>
"""
    else:
        return f"""
<h2>Privacy Policy</h2>
<p><strong>{pretty}</strong> takes user privacy seriously and processes personal information in accordance with applicable regulations.</p>
<h2>1. Information We Collect</h2>
<ul>
<li>Name and email address submitted through contact forms</li>
<li>IP address, cookies, and visit logs collected automatically</li>
<li>Site usage data and access logs</li>
</ul>
<h2>2. How We Use Your Information</h2>
<ul>
<li>Responding to inquiries and providing service information</li>
<li>Improving site services and conducting statistical analysis</li>
<li>Serving advertising and personalized content (e.g., Google AdSense)</li>
</ul>
<h2>3. Cookies</h2>
<p>This site uses third-party advertising services, including Google AdSense, which may use cookies. You can disable cookies through your browser settings at any time.</p>
<h2>4. Data Retention</h2>
<p>Collected personal information is deleted promptly once its purpose has been fulfilled, unless retention is required by applicable law.</p>
<p>For privacy-related inquiries, please contact us at {EMAIL}.</p>
"""


def fix_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    lang = site.get("lang", "en")
    theme = site.get("theme", "")
    domain, pretty = site_brand(site_url, theme)

    builders = {
        "about": build_about(domain, pretty, theme, lang),
        "contact": build_contact(domain, pretty, lang),
        "disclaimer": build_disclaimer(pretty, lang),
        "privacy-policy": build_privacy(pretty, lang),
    }

    log = {"site": site_url, "fixed": [], "skipped": []}
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                          params={"per_page": 100, "_fields": "id,title,link,content,slug"}, timeout=30)
        pages = r.json() if r.status_code == 200 else []
    except Exception as e:
        log["error"] = str(e)
        return log

    for slug, new_html in builders.items():
        title_key = slug.replace("-", " ")
        matches = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                   title_key in p["title"]["rendered"].strip().lower()]
        if not matches:
            log["skipped"].append({"slug": slug, "reason": "page_not_found"})
            continue

        p = matches[0]
        content = p.get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content)
        plain = re.sub(r'\s+', ' ', plain).strip()
        needs_fix = (len(plain) < MIN_LEN or "lorem ipsum" in content.lower() or EMAIL not in content)
        if not needs_fix:
            log["skipped"].append({"slug": slug, "reason": "already_ok"})
            continue

        pr = requests.patch(f"{site_url}/wp-json/wp/v2/pages/{p['id']}", auth=(WP_USER, pw),
                             json={"content": new_html}, timeout=25)
        log["fixed"].append({"slug": slug, "id": p["id"], "status": pr.status_code})
        time.sleep(0.8)

    return log


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = fix_site(site)
        results.append(res)
        print(f"{res['site']}: 수정{len(res.get('fixed',[]))} / 스킵{len(res.get('skipped',[]))} / 오류{res.get('error','')}")
        with open("all_pages_fix_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
