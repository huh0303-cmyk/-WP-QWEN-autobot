"""Owner-approved 2026-11-10 language-aware text and image routing contract.

This module defines the sole approved provider ordering. Platform publishers must
call this shared contract instead of legacy local fallback arrays.
"""
from __future__ import annotations

TEXT_MODELS = {
    "en": (
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-3.8-flash",
    ),
    "ko": (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
    ),
}
KOREAN_WORDPRESS_DOMAINS = frozenset(("koreanews365.com", "k-health365.com"))
KOREAN_BLOGSPOT_DOMAINS = frozenset(("koreanews365daily.blogspot.com",))
IMAGE_PAID_MODELS = ("bytonylee/sdxl-turbo", "black-forest-labs/flux-schnell")
IMAGE_FREE_SOURCES = ("pexels", "pixabay")


def normalize_language(language: str) -> str:
    value = (language or "").strip().lower().replace("_", "-")
    if value.startswith("ko") or value in ("korean", "한국어"):
        return "ko"
    if value.startswith("en") or value == "english":
        return "en"
    raise ValueError("Explicit content output language 'ko' or 'en' required")


def text_fallback_models(language: str) -> tuple[str, ...]:
    return TEXT_MODELS[normalize_language(language)]


def image_fallback_order(*, first_free_source: str) -> tuple[str, ...]:
    first = first_free_source.strip().lower()
    if first not in IMAGE_FREE_SOURCES:
        raise ValueError("first_free_source must be pexels or pixabay")
    second = next(x for x in IMAGE_FREE_SOURCES if x != first)
    return (first, second, *IMAGE_PAID_MODELS)
