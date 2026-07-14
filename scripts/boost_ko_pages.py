import os, sys, re, json, time, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

EMAIL = "huh0303@gmail.com"
TARGETS = ["https://k-health365.com", "https://ki-korea.com", "https://krealestate365.com",
           "https://kieca-korea.org", "https://ksa-korea.org", "https://koreanews365.com"]


def site_brand(site_url):
    domain = site_url.replace("https://", "").replace("http://", "").rstrip("/")
    name = domain.split(".")[0]
    pretty = re.sub(r'(365|org|com)$', '', name)
    pretty = pretty[0].upper() + pretty[1:] if pretty else name
    return domain, pretty


def build_about(domain, pretty, theme):
    return f"""
<h2>{pretty} 소개</h2>
<p><strong>{pretty}</strong>({domain})는 '{theme}' 분야의 실용적이고 신뢰할 수 있는 정보를 제공하는 것을 목표로 운영되는 정보 플랫폼입니다.</p>
<h2>운영 목적</h2>
<p>급변하는 정보 환경 속에서 정확하고 실질적으로 도움이 되는 콘텐츠를 찾기가 점점 어려워지고 있습니다. {pretty}는 이러한 문제를 해결하기 위해 관련 분야의 최신 동향과 실제 생활에 도움이 되는 정보를 체계적으로 정리하여 전달하고자 설립되었습니다. 저희는 단순히 정보를 나열하는 것이 아니라, 독자가 실제로 이해하고 활용할 수 있는 형태로 재구성하는 데 중점을 두고 있습니다.</p>
<h2>콘텐츠 원칙</h2>
<ul>
<li>공신력 있는 출처와 최신 자료를 기반으로 한 정보 작성</li>
<li>독자가 실생활에 바로 적용할 수 있는 실용적인 안내 제공</li>
<li>지속적인 콘텐츠 업데이트를 통한 최신성 유지</li>
<li>독자 관점에서 이해하기 쉬운 설명 방식 지향</li>
<li>과장되거나 확인되지 않은 정보의 배제</li>
</ul>
<h2>독자와의 소통</h2>
<p>{pretty}는 방문자 여러분의 의견을 소중히 생각합니다. 콘텐츠에 대한 제안, 오류 신고, 협업 문의 등 어떤 의견이든 아래 연락처를 통해 언제든 보내주시기 바랍니다. 보내주신 의견은 콘텐츠 개선에 실질적으로 반영됩니다.</p>
<ul>
<li><strong>이메일:</strong> {EMAIL}</li>
</ul>
<p>{pretty}는 앞으로도 방문자에게 더 나은 정보를 제공하기 위해 콘텐츠 품질 개선을 지속적으로 추진하겠습니다. 방문해 주셔서 진심으로 감사드립니다.</p>
"""


def build_contact(pretty):
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
<p>모든 문의는 영업일 기준으로 순차적으로 확인 후 답변드리고 있으며, 문의량에 따라 답변까지 다소 시간이 소요될 수 있는 점 양해 부탁드립니다. 급하신 문의사항은 제목에 별도로 표시해 주시면 우선적으로 확인하겠습니다.</p>
<p>{pretty}는 방문자 여러분의 의견을 소중히 생각하며, 더 나은 콘텐츠와 서비스를 만들기 위해 여러분의 피드백을 적극적으로 반영하고 있습니다. 소중한 시간 내어 연락해 주셔서 감사합니다.</p>
"""


log = []
for site_url in TARGETS:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    theme = site.get("theme", "")
    domain, pretty = site_brand(site_url)

    r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"per_page": 100, "_fields": "id,title,slug"}, timeout=30)
    pages = r.json() if r.status_code == 200 else []

    for slug, html in [("about", build_about(domain, pretty, theme)), ("contact", build_contact(pretty))]:
        title_key = slug.replace("-", " ")
        matches = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                   title_key in p["title"]["rendered"].strip().lower()]
        if not matches:
            log.append({"site": site_url, "slug": slug, "status": "not_found"})
            continue
        pid = matches[0]["id"]
        pr = requests.patch(f"{site_url}/wp-json/wp/v2/pages/{pid}", auth=(WP_USER, pw),
                             json={"content": html}, timeout=25)
        log.append({"site": site_url, "slug": slug, "id": pid, "status": pr.status_code})
        time.sleep(0.6)

with open("boost_ko_pages_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
