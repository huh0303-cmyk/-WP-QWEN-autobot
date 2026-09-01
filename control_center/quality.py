from __future__ import annotations

import re
from html import unescape
from typing import Any


MIN_SCORE = 75


def plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


def score_article(article: dict[str, Any], *, keyword: str, target_chars: int) -> tuple[int, list[str]]:
    title = str(article.get("title", "")).strip()
    meta = str(article.get("meta_description", "")).strip()
    content = str(article.get("content_html", ""))
    labels = article.get("labels") if isinstance(article.get("labels"), list) else []
    images = article.get("image_queries") if isinstance(article.get("image_queries"), list) else []
    text = plain_text(content)
    score = 0
    failures: list[str] = []
    keyword_terms = {x.lower() for x in re.findall(r"[A-Za-z0-9가-힣]{3,}", keyword)}
    title_terms = {x.lower() for x in re.findall(r"[A-Za-z0-9가-힣]{3,}", title)}

    if keyword_terms & title_terms:
        score += 15
    else:
        failures.append("제목에 핵심 키워드의 의미가 반영되지 않았습니다")
    if 20 <= len(title) <= 68:
        score += 10
    else:
        failures.append("제목은 20~68자여야 합니다")

    body_chars = len(re.sub(r"\s+", "", text))
    minimum = max(1100, int(target_chars * 0.75))
    maximum = int(target_chars * 1.35)
    if minimum <= body_chars <= maximum:
        score += 20
    else:
        failures.append(f"본문 길이 {body_chars}자: 허용 범위 {minimum}~{maximum}자")

    if 110 <= len(meta) <= 130:
        score += 15
    else:
        failures.append("검색 설명은 110~130자여야 합니다")
    if 3 <= len(labels) <= 5 and all(1 <= len(str(x).split()) <= 4 for x in labels):
        score += 10
    else:
        failures.append("태그는 관련성 높은 짧은 항목 3~5개여야 합니다")

    headings = len(re.findall(r"(?is)<h[23](?:\s[^>]*)?>", content))
    if headings >= 3:
        score += 10
    else:
        failures.append("유용한 H2/H3 소제목이 3개 이상 필요합니다")

    first_part = text[:450].lower()
    if any(term in first_part for term in keyword_terms):
        score += 5
    else:
        failures.append("도입부가 핵심 키워드를 직접 다루지 않습니다")

    artificial = re.findall(r"(?i)\b(as an ai|language model|in conclusion|delve into|unlock the secrets|comprehensive guide)\b", text)
    if not artificial:
        score += 5
    else:
        failures.append("AI 상투 표현이 발견됐습니다")

    ymyl = bool(re.search(r"(?i)(visa|immigration|insurance|medical|hospital|treatment|tax|law|finance|비자|보험|의료|세금|법률|금융)", keyword + " " + text))
    has_date = bool(re.search(r"(?i)(as of|effective|기준|20\d{2})", text))
    has_warning = bool(re.search(r"(?i)(can change|subject to change|verify|official|consult|not .* advice|변경|공식|확인|상담|자문이 아닙니다)", text))
    if not ymyl or (has_date and has_warning):
        score += 10
    else:
        failures.append("민감 분야의 기준일·변경 가능성·면책 또는 공식 확인 안내가 부족합니다")

    if len(images) > 2:
        failures.append("이미지 후보는 0~2개만 허용됩니다")
        score = min(score, 74)
    return min(score, 100), failures

