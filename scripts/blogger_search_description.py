#!/usr/bin/env python3
"""Blogger per-post search-description rules shared by API and local UI."""

MIN_CHARS = 100
MAX_CHARS_EXCLUSIVE = 120


def build_search_description(keyword: str) -> str:
    topic = " ".join(str(keyword).split()).strip(" .—-")
    korean = any("가" <= char <= "힣" for char in topic)
    if korean:
        value = f"{topic}의 핵심 조건과 준비 절차, 비용, 주의사항을 실제 확인 순서에 맞춰 알기 쉽게 정리합니다. 신청하거나 결정하기 전에 최신 공식 정보와 변경 사항까지 함께 확인하세요."
    else:
        value = f"Practical guidance on {topic}, covering key steps, costs, checks, and current details to review before acting."
    if len(value) >= MAX_CHARS_EXCLUSIVE:
        value = value[: MAX_CHARS_EXCLUSIVE - 2].rstrip(" ,;:-") + "."
    suffix = " 최신 기준을 확인하세요." if korean else " Check current official guidance."
    while len(value) < MIN_CHARS:
        room = MAX_CHARS_EXCLUSIVE - 1 - len(value)
        if room <= 0:
            break
        value = value.rstrip(".") + suffix[:room]
    value = value[: MAX_CHARS_EXCLUSIVE - 1].rstrip(" ,;:-")
    if value and value[-1] not in ".!?。":
        value = (value[:-1].rstrip() + ".") if len(value) == MAX_CHARS_EXCLUSIVE - 1 else value + "."
    if not MIN_CHARS <= len(value) < MAX_CHARS_EXCLUSIVE:
        raise ValueError(f"invalid Blogger search description length: {len(value)}")
    return value
