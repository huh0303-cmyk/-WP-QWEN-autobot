import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kieca-korea.org")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

ABOUT_HTML = """
<h2>KIECA Korea 소개</h2>
<p><strong>KIECA Korea</strong>(Korea International Education &amp; Culture Association)는 한국과 해외 학생 및 교육기관을 잇는 국제교육·문화 정보 플랫폼입니다.</p>
<p>한국 유학, 어학연수, 문화교류를 준비하는 분들에게 실질적으로 도움이 되는 정보를 제공하는 것을 목표로 운영하고 있으며, 한국 대학(원) 및 교육기관과의 협력 네트워크를 기반으로 신뢰할 수 있는 콘텐츠를 발행합니다.</p>
<h2>운영 방향</h2>
<ul>
<li>한국 유학·교육 제도에 대한 정확하고 최신화된 정보 제공</li>
<li>외국인 학생의 한국 생활 적응을 돕는 실용 가이드 발행</li>
<li>한국 대학 및 교육기관과의 협력을 통한 검증된 정보 유통</li>
</ul>
<p>본 사이트의 콘텐츠는 지속적으로 업데이트되며, 보다 정확한 정보 제공을 위해 최선을 다하고 있습니다.</p>
"""

CONTACT_HTML = """
<h2>문의하기</h2>
<p>KIECA Korea 운영팀에 궁금하신 사항이나 협력 제안을 보내주시면 순차적으로 답변드리겠습니다.</p>
<h3>연락처</h3>
<ul>
<li><strong>이메일:</strong> huh0303@gmail.com</li>
<li><strong>전화:</strong> +82-10-3790-6635</li>
</ul>
<p>이메일 문의 시 문의 내용과 연락 가능한 연락처를 함께 남겨주시면 빠른 답변에 도움이 됩니다.</p>
"""

for path, title, html in [("contact", "Contact", CONTACT_HTML), ("about", "About", ABOUT_HTML)]:
    r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"slug": path}, timeout=20)
    matches = r.json()
    if not matches:
        print(f"{title} 페이지를 못 찾음"); continue
    pid = matches[0]["id"]
    pr = requests.patch(f"{base}/wp-json/wp/v2/pages/{pid}", auth=(WP_USER, pw),
                         json={"content": html}, timeout=25)
    print(f"{title} (id={pid}) 업데이트: {pr.status_code}")

with open("kieca_pages_fix_result.json", "w", encoding="utf-8") as f:
    json.dump({"done": True}, f)
