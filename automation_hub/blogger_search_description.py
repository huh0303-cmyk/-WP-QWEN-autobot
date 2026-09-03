from __future__ import annotations

import re

MIN_CHARS = 100
MAX_CHARS = 120


def validate_search_description(value: str) -> str:
    normalized = " ".join(str(value or "").split())
    if not MIN_CHARS <= len(normalized) <= MAX_CHARS:
        raise ValueError(f"Blogger search description must be {MIN_CHARS}-{MAX_CHARS} characters")
    return normalized


def build_search_description(*, title: str, topic: str, language: str) -> str:
    title = " ".join(str(title).split())
    topic = " ".join(str(topic).split())
    if language.lower().startswith("ko"):
        text = f"{title}: {topic}의 핵심 기준과 확인 순서, 실용적인 체크리스트를 신뢰할 수 있는 출처 중심으로 알기 쉽게 정리합니다."
        filler = " 최신 기준과 주의사항도 함께 확인하세요."
    else:
        text = f"{title}: practical, source-aware guidance on {topic}, with clear steps, useful checks, and cautions for informed decisions."
        filler = " Review the latest official guidance before acting."
    while len(text) < MIN_CHARS:
        text = text.rstrip(".") + filler
    if len(text) > MAX_CHARS:
        clipped = text[: MAX_CHARS - 1].rstrip(" ,;:-")
        clipped = re.sub(r"\s+\S*$", "", clipped) if language.lower().startswith("en") else clipped
        text = clipped.rstrip(".") + "."
    return validate_search_description(text)
