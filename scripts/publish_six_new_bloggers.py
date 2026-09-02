#!/usr/bin/env python3
"""Publish one carefully scoped launch article to the six newly discovered blogs."""
from __future__ import annotations

import json
import os
import sys
from datetime import date

import requests

sys.path.insert(0, os.path.dirname(__file__))
from openai_text import openai_generate_text  # noqa: E402
from replicate_image_provider import generate_image_url  # noqa: E402


SITES = [
    {
        "key": "kwellnesslab", "id": "4456888951628869767", "url": "https://glow.k-health365.com",
        "title": "K-Wellness and K-Beauty: A Practical Guide to Building a Safe Korean Routine",
        "labels": ["K-Wellness", "K-Beauty", "Korean skincare", "wellness", "beauty routine", "skin health", "self care", "Korea"],
        "intro": "K-Wellness Lab explains Korean health and beauty without hype. Our focus is a sustainable routine: understand your skin and lifestyle, introduce one change at a time, and separate cosmetic advice from medical care.",
        "sections": [
            ("Start with health, not trends", "Sleep, hydration, balanced meals, movement and sun protection form the base of any beauty routine. A viral product cannot compensate for irritation, chronic sleep loss or an untreated skin condition. Track comfort, redness and dryness before chasing instant results."),
            ("Build a simple K-beauty routine", "Begin with a gentle cleanser, moisturizer and broad-spectrum sunscreen. Add only one optional step—such as a hydrating toner or targeted serum—after the basics feel comfortable. Patch-test new products and stop when burning, swelling or persistent redness appears."),
            ("Read labels and claims carefully", "Ingredient lists help identify fragrance, exfoliating acids, retinoids and other actives, but concentration and formulation also matter. Terms such as clean, natural or dermatologist-tested do not guarantee that a product suits every person."),
            ("When professional advice matters", "Persistent acne, eczema-like symptoms, infection, sudden hair loss or a changing lesion deserve assessment by a qualified clinician. Beauty content is educational and should not replace diagnosis or treatment."),
        ],
        "ending": "Future K-Wellness Lab guides will cover Korean skincare categories, scalp and body care, wellness habits, product comparisons and evidence-aware beauty trends.",
    },
    {
        "key": "kmedicaljobs", "id": "3205814823967421343", "url": "https://k-health365-edu.blogspot.com",
        "title": "Medical Careers in Korea: How to Map the Right Qualification Path",
        "labels": ["medical careers", "healthcare jobs", "Korea jobs", "medical license", "certification", "career guide", "healthcare education", "Korea"],
        "intro": "K-Medical Job Center introduces healthcare occupations and the qualifications behind them. The first rule is that job title, legal scope of practice and licensing authority must be checked separately—especially for applicants trained outside Korea.",
        "sections": [
            ("Separate licensed and non-licensed roles", "Doctors, dentists, nurses, pharmacists and several allied-health occupations are regulated. Hospitals also employ coordinators, administrators, medical translators, researchers, data specialists and customer-service staff whose requirements differ by employer."),
            ("Create a qualification checklist", "For each target role, record the responsible Korean authority, recognized degree, examination requirements, language expectations, document authentication, continuing education and renewal rules. Never rely on a translated job title alone."),
            ("Foreign credentials need individual review", "A qualification earned abroad does not automatically grant permission to practise in Korea. Applicants may need eligibility screening, verified transcripts, licensing examinations, immigration status and Korean-language evidence. Requirements can change, so confirm them with the relevant ministry, licensing body and employer."),
            ("Build employable evidence", "Keep a portfolio of verified education, clinical or project experience, references and role-specific skills. For non-clinical roles, health-data literacy, terminology, privacy awareness, communication and bilingual ability can be valuable."),
        ],
        "ending": "We will publish occupation profiles, qualification roadmaps and application checklists. Every regulatory guide will identify the official authority readers should confirm before applying.",
    },
    {
        "key": "korealifesupport", "id": "2531035487222435079", "url": "https://korea-life-support365.blogspot.com",
        "title": "정부 지원금·보조금·생활 혜택을 정확하게 찾는 방법",
        "labels": ["정부지원금", "보조금", "복지혜택", "생활지원", "정책정보", "신청자격", "공공서비스", "대한민국"],
        "intro": "한국생활지원정보는 정부 지원금, 지자체 보조금, 생활 혜택을 전문적으로 정리하는 블로그입니다. 같은 이름의 사업도 거주지·나이·소득·가구 형태와 신청 시점에 따라 조건이 달라질 수 있으므로 반드시 공식 공고를 기준으로 확인해야 합니다.",
        "sections": [
            ("먼저 확인할 네 가지", "지원 대상, 소득·재산 기준, 신청 기간, 중복 수급 제한을 먼저 확인합니다. 안내 글에 금액만 강조돼 있어도 실제 지급액과 방식은 개인 조건 및 예산에 따라 달라질 수 있습니다."),
            ("공식 경로에서 교차 확인", "정부24, 복지로, 고용24, 보조금24와 해당 지방자치단체 홈페이지에서 최신 공고를 확인합니다. 문자나 SNS 링크에서 계좌 비밀번호·인증번호를 요구한다면 진행하지 말고 공식 대표번호로 문의해야 합니다."),
            ("신청 전 준비", "신분·거주·가구·소득·재산·재직 상태를 증명할 서류를 확인하고 제출 기한을 기록합니다. 온라인 신청이 어려우면 주민센터나 담당 기관에 본인 상황을 설명하고 필요한 서류를 다시 확인합니다."),
            ("전문 정보의 기준", "앞으로 각 글에는 기준일, 담당 기관, 공식 확인 링크, 핵심 자격, 신청 기간, 필요 서류와 주의사항을 분리해 제시합니다. 확정되지 않은 혜택이나 출처가 불명확한 금액은 단정하지 않습니다."),
        ],
        "ending": "이 블로그의 정보는 이해를 돕기 위한 안내이며 수급 자격을 보장하지 않습니다. 최종 결정은 해당 사업의 최신 공식 공고와 담당 기관의 판단을 따릅니다.",
    },
    {
        "key": "koreamedicaltour1", "id": "2234527810530371008", "url": "https://koreamedicaltour1.blogspot.com",
        "title": "Planning Medical Travel to Korea: A Safety-First Checklist",
        "labels": ["Korea medical tourism", "medical travel", "Korean hospitals", "patient guide", "treatment planning", "aftercare", "medical interpreter", "Korea"],
        "intro": "Korea Medical Tour helps international patients plan care in Korea with realistic expectations. A safe journey begins with clinical suitability, transparent costs and a written aftercare plan—not with travel packages or promotional before-and-after images.",
        "sections": [
            ("Verify the provider and clinician", "Confirm the medical institution, the treating professional’s credentials and who will perform each part of the procedure. Ask how complications are handled and whether interpretation is independent and medically competent."),
            ("Get a written treatment plan", "Request the proposed procedure, alternatives, expected recovery, material risks, total estimated charges, cancellation terms and likely additional costs. Remote advice is preliminary; the plan may change after an in-person examination."),
            ("Plan recovery before booking flights", "Allow time for tests, follow-up and travel restrictions. Arrange accommodation, medication records, emergency contacts and support after discharge. Check whether travel insurance covers planned treatment and complications."),
            ("Take records home", "Ask for discharge instructions, prescriptions, procedure and implant details, test results and a contact for post-treatment questions. Know which symptoms require urgent care and arrange follow-up with a clinician at home."),
        ],
        "ending": "This site will cover provider-check questions, procedure planning, interpreters, budgets, recovery and destination logistics. It offers general education, not medical diagnosis or a recommendation of a particular clinic.",
    },
    {
        "key": "kworld365_kpop", "id": "3683978748331752523", "url": "https://kworld365.blogspot.com",
        "title": "Your K-Pop Guide: How to Follow Comebacks, Performances and Fandom Safely",
        "labels": ["K-pop", "Korean music", "comeback guide", "K-pop fandom", "music shows", "Korean culture", "concert guide", "Korea"],
        "intro": "KWorld365 is a dedicated K-pop guide for fans who want clear context, reliable schedules and thoughtful coverage. We will focus on music, artists, performances, releases and fandom culture while distinguishing official announcements from rumours.",
        "sections": [
            ("Follow primary sources", "Use the artist’s official accounts, label notices, verified ticket sellers and broadcaster schedules for comeback dates, concerts and fan events. Time zones and schedule changes matter, so note the original publication time and check again before travelling."),
            ("Understand the comeback cycle", "A release may include concept photos, track lists, teasers, a music video, showcase appearances and broadcast stages. Our guides will connect these pieces so new fans can follow without treating every teaser or fan theory as confirmed information."),
            ("Support artists responsibly", "Stream and purchase within your budget, respect venue rules and privacy, and avoid unofficial sellers asking for unsafe payment methods. Healthy fandom leaves room for school, work, rest and different opinions."),
            ("What we will cover", "Expect comeback calendars, artist introductions, song and performance context, award and chart explainers, concert preparation, official merchandise guides and accessible summaries of Korean entertainment terminology."),
        ],
        "ending": "KWorld365 will celebrate K-pop with enthusiasm and accuracy. Sources will be identified, rumours will be labelled, and corrections will be made when official information changes.",
    },
    {
        "key": "seoulintlschoolguide", "id": "8077962392257357260", "url": "https://seoulintlschoolguide.blogspot.com",
        "title": "Choosing an International School in Seoul: A Family Decision Framework",
        "labels": ["international schools Seoul", "international education", "school admissions", "Seoul families", "curriculum", "school fees", "student life", "Korea"],
        "intro": "Seoul International School Guide helps families compare international schools, foreign schools and internationally oriented university pathways in Korea. The right choice depends on eligibility, curriculum, student support, commute and long-term education plans—not reputation alone.",
        "sections": [
            ("Confirm school type and eligibility", "Names used in everyday conversation can hide important legal and admissions differences. Ask the school which students it may enroll, what documents prove eligibility and whether current accreditation or recognition matches your family’s future destination."),
            ("Compare the complete curriculum", "Look beyond a programme label. Review subjects, language support, assessment, graduation requirements, university counselling, learning support, class size and how transfers are handled. Ask for outcomes with appropriate context rather than relying on a single success story."),
            ("Calculate the full family cost", "Tuition may not include application fees, buses, meals, devices, uniforms, activities, trips or capital charges. Confirm refund and withdrawal policies in writing and calculate the daily commute at realistic Seoul traffic times."),
            ("Visit with focused questions", "Observe classroom culture, safeguarding, communication with parents, student wellbeing and facilities actually used by your child’s age group. Speak with admissions staff about your child’s specific language, learning and transition needs."),
        ],
        "ending": "Future guides will compare curricula, admissions stages, costs, locations, university pathways and family life. Always verify current details directly with each institution before applying or paying a fee.",
    },
]


def token() -> str:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def article_html(site: dict) -> str:
    parts = [f"<!-- launch-six:{site['key']}:2026-09-03 -->", f"<p>{site['intro']}</p>"]
    for heading, body in site["sections"]:
        parts.extend((f"<h2>{heading}</h2>", f"<p>{body}</p>"))
    parts.extend(("<h2>Our editorial promise</h2>", f"<p>{site['ending']}</p>",
                  f"<p><em>Reviewed for publication on {date.today().isoformat()}. Check current official requirements before acting.</em></p>"))
    return "\n".join(parts)


def generated_article(site: dict) -> tuple[str, str, list[str], str]:
    """Use the locked network engines; fail closed instead of publishing filler."""
    source = article_html(site)
    prompt = f"""You are the expert editor for {site['url']}.
Rewrite the supplied editorial brief into one original, accurate, helpful launch article.
Return ONLY a JSON object with keys title, content_html, labels, image_subject.
Rules: preserve the site's exact subject and all safety cautions; use the brief's language;
900-1300 words for English or 1800-3000 Korean characters; HTML body with short paragraphs,
H2 sections, one actionable checklist, and a concise conclusion; no invented statistics,
prices, deadlines, certifications, institutions or guarantees; 8-12 short SEO labels;
image_subject describes a realistic editorial 16:9 scene with no text or logos.

EDITORIAL BRIEF:
{source}
"""
    raw = openai_generate_text(prompt, temperature=0.4, max_retries=3).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].lstrip()
    data = json.loads(raw)
    title = str(data["title"]).strip()
    content = str(data["content_html"]).strip()
    # Blogger rejects a post with a generic INVALID_ARGUMENT when generated
    # label values exceed its undocumented aggregate constraints. Preserve
    # the approved, short site taxonomy for deterministic publishing.
    labels = site["labels"]
    subject = str(data["image_subject"]).strip()
    if not title or len(content) < 1500 or not (8 <= len(labels) <= 12) or not subject:
        raise RuntimeError(f"GPT-5 mini output failed quality gate for {site['key']}")
    image_url = generate_image_url(subject, theme=title)
    if not image_url:
        raise RuntimeError(f"SDXL-Lightning and FLUX Schnell both failed for {site['key']}")
    marker = f"<!-- launch-six:{site['key']}:2026-09-03 -->"
    hero = f'<figure><img src="{image_url}" alt="{title}" loading="eager"/><figcaption>Editorial image created for this guide.</figcaption></figure>'
    return title, f"{marker}\n{hero}\n{content}", labels, image_url


def main() -> int:
    access = token()
    headers = {"Authorization": f"Bearer {access}"}
    results = []
    failed = False
    for site in SITES:
        endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{site['id']}/posts"
        marker = f"launch-six:{site['key']}:2026-09-03"
        existing = requests.get(endpoint, params={"status": ["draft", "live", "scheduled"], "view": "ADMIN", "fetchBodies": "true", "maxResults": 100}, headers=headers, timeout=30)
        existing.raise_for_status()
        match = next((p for p in existing.json().get("items", []) if marker in str(p.get("content", ""))), None)
        if match:
            results.append({"site": site["key"], "status": "existing", "url": match.get("url", ""), "post_id": match.get("id", "")})
            continue
        title, content, labels, image_url = generated_article(site)
        response = requests.post(endpoint, params={"isDraft": "false"}, headers=headers, json={
            "kind": "blogger#post", "title": title, "content": content, "labels": labels
        }, timeout=30)
        if response.status_code not in {200, 201}:
            failed = True
            results.append({"site": site["key"], "status": "failed", "http": response.status_code, "error": response.text[:500]})
            continue
        post = response.json()
        public_url = post.get("url", "")
        check = requests.get(public_url, timeout=30)
        ok = check.status_code == 200 and title in check.text and image_url in check.text
        results.append({"site": site["key"], "status": "published" if ok else "verification_failed", "url": public_url, "post_id": post.get("id", ""), "http": check.status_code, "title": title, "image_url": image_url})
        failed = failed or not ok
    with open("six_blogger_publish_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
