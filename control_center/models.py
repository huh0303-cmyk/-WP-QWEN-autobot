from __future__ import annotations

# Single source of truth: config/LONDON_PROJECT_UNIFIED_CONTENT_POLICY_20261114.json
# Legacy GPT/OpenAI writer entries are intentionally removed from the control UI.
TEXT_MODELS = {
    "gemini-3.6-flash": {"label": "Gemini 3.6 Flash", "price": "free-tier", "description": "English primary"},
    "gemini-3.5-flash": {"label": "Gemini 3.5 Flash", "price": "free-tier", "description": "English fallback"},
    "gemini-3.5-flash-lite": {"label": "Gemini 3.5 Flash Lite", "price": "free-tier", "description": "English fallback"},
    "gemini-3.1-flash-lite": {"label": "Gemini 3.1 Flash Lite", "price": "free-tier", "description": "English fallback"},
    "gemini-3.0-flash-lite": {"label": "Gemini 3.0 Flash Lite", "price": "free-tier", "description": "Korean primary"},
    "gemini-3.1-flash": {"label": "Gemini 3.1 Flash", "price": "free-tier", "description": "Korean fallback"},
    "gemini-3.0-flash": {"label": "Gemini 3.0 Flash", "price": "free-tier", "description": "Korean fallback"},
    "gemini-2.0-flash": {"label": "Gemini 2.0 Flash", "price": "free-tier", "description": "Universal fallback"},
    "gemini-3.8-flash": {"label": "Gemini 3.8 Flash", "price": "free-tier", "description": "Final fallback"},
}

IMAGE_MODELS = {
    "auto": {"label": "Pexels → Pixabay → SDXL Turbo → FLUX Schnell", "price": "free-first", "description": "Unified London Project image policy"},
    "none": {"label": "No image", "price": "$0/image", "description": "Only when all relevant image providers fail"},
}

DEFAULT_TEXT_MODEL = "gemini-3.0-flash-lite"
DEFAULT_IMAGE_MODEL = "auto"


def require_text_model(model: str) -> str:
    if model not in TEXT_MODELS:
        raise ValueError("지원하지 않는 글쓰기 엔진입니다")
    return model


def require_image_model(model: str) -> str:
    if model not in IMAGE_MODELS:
        raise ValueError("지원하지 않는 이미지 엔진입니다")
    return model
