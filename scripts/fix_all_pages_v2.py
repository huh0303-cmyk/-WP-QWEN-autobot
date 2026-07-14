# -*- coding: utf-8 -*-
import os, sys, re, json, time, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

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
<p>급변하는 정보 환경 속에서 정확하고 실질적으로 도움이 되는 콘텐츠를 찾기가 점점 어려워지고 있습니다. {pretty}는 이러한 문제를 해결하기 위해 관련 분야의 최신 동향과 실제 생활에 도움이 되는 정보를 체계적으로 정리하여 전달하고자 설립되었습니다.</p>
<h2>콘텐츠 원칙</h2>
<ul>
<li>공신력 있는 출처와 최신 자료를 기반으로 한 정보 작성</li>
<li>독자가 실생활에 바로 적용할 수 있는 실용적인 안내 제공</li>
<li>지속적인 콘텐츠 업데이트를 통한 최신성 유지</li>
<li>독자 관점에서 이해하기 쉬운 설명 방식 지향</li>
</ul>
<h2>독자와의 소통</h2>
<p>{pretty}는 방문자 여러분의 의견을 소중히 생각합니다. 콘텐츠에 대한 제안, 오류 신고, 협업 문의 등 어떤 의견이든 아래 연락처를 통해 언제든 보내주시기 바랍니다.</p>
<ul>
<li><strong>이메일:</strong> {EMAIL}</li>
</ul>
<p>{pretty}는 앞으로도 방문자에게 더 나은 정보를 제공하기 위해 콘텐츠 품질 개선을 지속적으로 추진하겠습니다. 방문해 주셔서 감사합니다.</p>
"""
    else:
        return f"""
<h2>About {pretty}</h2>
<p><strong>{pretty}</strong> ({domain}) is an information platform dedicated to providing practical, reliable content in the field of {theme}.</p>
<h2>Our Mission</h2>
<p>In a fast-changing information landscape, finding accurate and genuinely useful content can be difficult. {pretty} was created to address this gap by curating up-to-date, well-organized, and practical information that readers can actually use in their daily lives.</p>
<h2>Our Content Principles</h2>
<ul>
<li>Content based on credible, well-researched, and current sources</li>
<li>Practical guidance readers can apply immediately to their situation</li>
<li>Ongoing updates to keep information accurate and relevant</li>
<li>Clear, reader-friendly explanations rather than overly technical language</li>
</ul>
<h2>Get in Touch</h2>
<p>{pretty} values feedback from our readers. Whether you have a content suggestion, spotted an error, or are interested in a partnership, please feel free to reach out anytime.</p>
<ul>
<li><strong>Email:</strong> {EMAIL}</li>
</ul>
<p>{pretty} is committed to continuously improving the quality of our content for our readers. Thank you for visiting.</p>
"""


def build_contact(domain, pretty, theme, lang):
    if lang == "ko":
        return f"""
<h2>문의하기</h2>
<p>{pretty} 운영팀에 궁금하신 사항이 있으시면 언제든 편하게 연락해 주시기 바랍니다. 콘텐츠 관련 문의, 오류 신고, 제휴 및 협업 제안, 광고 문의 등 모든 사항을 환영합니다.</p>
<h3>연락처</h3>
<ul>
<li><strong>이메일:</strong> {EMAIL}</li>
</ul>
<h3>문의 시 참고사항</h3>
<p>이메일 문의 시 아래 내용을 함께 남겨주시면 더 정확하고 빠른 답변을 드리는 데 도움이 됩니다.</p>
<ul>
<li>문의 제목 및 구체적인 내용</li>
<li>관련 페이지 URL (해당하는 경우)</li>
<li>회신받을 연락처</li>
</ul>
<p>모든 문의는 영업일 기준으로 순차적으로 확인 후 답변드리고 있으며, 문의량에 따라 답변까지 다소 시간이 소요될 수 있는 점 양해 부탁드립니다.</p>
<p>{pretty}는 방문자 여러분의 의견을 소중히 생각하며, 더 나은 콘텐츠와 서비스를 만들기 위해 여러분의 피드백을 적극적으로 반영하고 있습니다. 소중한 시간 내어 연락해 주셔서 감사합니다.</p>
"""
    else:
        return f"""
<h2>Contact Us</h2>
<p>If you have any questions, feedback, or inquiries about our content, please feel free to reach out to the {pretty} team. We welcome content-related inquiries, error reports, partnership proposals, and advertising inquiries.</p>
<h3>Contact Information</h3>
<ul>
<li><strong>Email:</strong> {EMAIL}</li>
</ul>
<h3>What to Include in Your Message</h3>
<p>To help us respond accurately and promptly, please include the following when reaching out:</p>
<ul>
<li>A clear subject and detailed description of your inquiry</li>
<li>The relevant page URL, if applicable</li>
<li>A contact email where we can reach you</li>
</ul>
<p>We review and respond to all inquiries on a rolling basis during business days. Please note that response times may vary depending on inquiry volume.</p>
<p>{pretty} genuinely values feedback from our readers and actively uses it to improve the quality of our content and overall service. Thank you for taking the time to reach out to us.</p>
"""


def build_disclaimer(pretty, theme, lang):
    if lang == "ko":
        return f"""
<h2>면책조항 (Disclaimer)</h2>
<p><strong>{pretty}</strong>에서 제공하는 모든 정보는 '{theme}' 분야에 대한 일반적인 참고 목적으로 제공되며, 특정 개인의 상황에 대한 전문적인 조언을 대체하지 않습니다.</p>
<h2>1. 정보의 정확성 및 최신성</h2>
<p>본 사이트의 콘텐츠는 신뢰할 수 있는 출처를 바탕으로 작성 및 검토되었으나, 정보의 완전성, 정확성, 최신성을 완전히 보장하지는 않습니다. 관련 제도나 정책은 수시로 변경될 수 있으므로, 중요한 결정을 내리기 전에는 반드시 최신 공식 정보를 별도로 확인하시기 바랍니다.</p>
<h2>2. 법적 책임의 제한</h2>
<p>본 사이트에 게재된 정보를 근거로 한 개인 또는 기관의 결정이나 행동, 그로 인해 발생하는 직간접적인 손해에 대해 당사는 어떠한 법적 책임도 지지 않습니다.</p>
<h2>3. 전문가 상담 권장</h2>
<p>본 사이트의 콘텐츠는 법률, 금융, 의료, 세무, 이민 등 전문 자격이 필요한 분야의 조언을 대체하지 않습니다. 개인적인 상황에 적합한 결정을 내리기 위해서는 반드시 해당 분야의 자격을 갖춘 전문가와 상담하시기 바랍니다.</p>
<h2>4. 외부 링크에 대한 책임</h2>
<p>본 사이트는 독자의 편의를 위해 외부 사이트로 연결되는 링크를 포함할 수 있습니다. 외부 사이트의 콘텐츠, 정확성, 개인정보 처리방침에 대해서는 당사가 책임지지 않습니다.</p>
<p>본 면책조항 관련 문의사항은 {EMAIL}으로 연락 주시기 바랍니다.</p>
"""
    else:
        return f"""
<h2>Disclaimer</h2>
<p>All information provided by <strong>{pretty}</strong> in the field of {theme} is for general informational purposes only and does not constitute professional advice tailored to any individual's specific situation.</p>
<h2>1. Accuracy and Timeliness of Information</h2>
<p>While our content is researched and prepared using credible sources, we do not guarantee its completeness, accuracy, or timeliness. Relevant policies and regulations may change over time, so please verify important information through official, up-to-date sources before making any significant decisions.</p>
<h2>2. Limitation of Liability</h2>
<p>We are not liable for any direct or indirect damages resulting from decisions or actions taken by individuals or organizations based on content published on this site.</p>
<h2>3. Professional Consultation Recommended</h2>
<p>Content on this site does not replace professional legal, financial, medical, tax, or immigration advice. Please consult a qualified professional in the relevant field before making decisions specific to your circumstances.</p>
<h2>4. External Links</h2>
<p>This site may contain links to external websites for readers' convenience. We are not responsible for the content, accuracy, or privacy practices of external sites.</p>
<p>For questions regarding this disclaimer, please contact us at {EMAIL}.</p>
"""


def build_privacy(pretty, lang):
    if lang == "ko":
        return f"""
<h2>개인정보처리방침</h2>
<p><strong>{pretty}</strong>는 이용자의 개인정보를 중요하게 생각하며, 관련 법령을 준수하여 개인정보를 처리하고 있습니다. 본 방침은 사전 고지 없이 변경될 수 있으며, 변경 시 본 페이지를 통해 공지합니다.</p>
<h2>1. 수집하는 개인정보 항목</h2>
<p>본 사이트는 서비스 제공을 위해 다음과 같은 정보를 수집할 수 있습니다.</p>
<ul>
<li>문의 시 이용자가 직접 입력하는 이름, 이메일 주소</li>
<li>접속 IP 주소, 쿠키, 브라우저 정보 등 자동 수집 정보</li>
<li>서비스 이용 기록 및 접속 로그</li>
</ul>
<h2>2. 개인정보의 수집 및 이용 목적</h2>
<ul>
<li>이용자 문의에 대한 응답 및 서비스 안내</li>
<li>사이트 서비스 개선 및 이용 통계 분석</li>
<li>Google AdSense 등 제3자 광고 서비스를 통한 맞춤형 광고 제공</li>
</ul>
<h2>3. 쿠키(Cookie) 사용</h2>
<p>본 사이트는 Google AdSense를 포함한 제3자 광고 서비스를 이용하고 있으며, 이 과정에서 쿠키가 사용될 수 있습니다. 이용자는 브라우저 설정을 통해 언제든지 쿠키 저장을 거부하거나 삭제할 수 있습니다.</p>
<h2>4. 개인정보의 보유 및 파기</h2>
<p>수집된 개인정보는 수집 및 이용 목적이 달성된 후 지체 없이 파기하며, 관련 법령에 따라 일정 기간 보존이 필요한 경우 해당 기간 동안 안전하게 보관합니다.</p>
<h2>5. 문의처</h2>
<p>개인정보 처리와 관련한 문의사항은 {EMAIL}으로 연락 주시기 바랍니다.</p>
"""
    else:
        return f"""
<h2>Privacy Policy</h2>
<p><strong>{pretty}</strong> takes user privacy seriously and processes personal information in accordance with applicable data protection regulations. This policy may be updated from time to time, and any changes will be posted on this page.</p>
<h2>1. Information We Collect</h2>
<ul>
<li>Name and email address voluntarily submitted through contact forms</li>
<li>IP address, cookies, and browser information collected automatically</li>
<li>Site usage data and access logs</li>
</ul>
<h2>2. How We Use Your Information</h2>
<ul>
<li>Responding to inquiries and providing service-related information</li>
<li>Improving site services and analyzing usage statistics</li>
<li>Serving personalized advertising through third-party services such as Google AdSense</li>
</ul>
<h2>3. Cookies</h2>
<p>This site uses third-party advertising services, including Google AdSense, which may use cookies to serve ads based on prior visits. You can disable or delete cookies at any time through your browser settings.</p>
<h2>4. Data Retention</h2>
<p>Collected personal information is deleted promptly once its purpose has been fulfilled, unless a longer retention period is required by applicable law.</p>
<h2>5. Contact</h2>
<p>For any privacy-related inquiries, please contact us at {EMAIL}.</p>
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
        "contact": build_contact(domain, pretty, theme, lang),
        "disclaimer": build_disclaimer(pretty, theme, lang),
        "privacy-policy": build_privacy(pretty, lang),
    }

    log = {"site": site_url, "fixed": [], "skipped": []}
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                          params={"per_page": 100, "_fields": "id,title,link,slug"}, timeout=30)
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
        pr = requests.patch(f"{site_url}/wp-json/wp/v2/pages/{p['id']}", auth=(WP_USER, pw),
                             json={"content": new_html}, timeout=25)
        log["fixed"].append({"slug": slug, "id": p["id"], "status": pr.status_code})
        time.sleep(0.6)

    return log


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = fix_site(site)
        results.append(res)
        print(f"{res['site']}: 수정{len(res.get('fixed',[]))} / 스킵{len(res.get('skipped',[]))} / 오류{res.get('error','')}")
        with open("all_pages_fix_v2_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
