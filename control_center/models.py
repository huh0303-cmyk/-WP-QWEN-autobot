from __future__ import annotations

TEXT_MODELS = {
    "gemini-2.5-flash-lite": {"label": "Gemini 2.5 Flash-Lite", "price": "$0.0007/글", "description": "일반 글 · 최저비용"},
    "gemini-2.5-flash": {"label": "Gemini 2.5 Flash", "price": "$0.0041/글", "description": "비자·금융·의료 검토"},
    "gpt-5-mini": {"label": "GPT-5 mini", "price": "$0.0033/글", "description": "전체 블로그 기본 작성 엔진"},
    "gpt-5.4-mini": {"label": "GPT-5.4 mini", "price": "$0.0075/글", "description": "최중요 글"},
}

IMAGE_MODELS = {
    "auto": {"label": "Pexels → Pixabay → SDXL Turbo → FLUX Schnell", "price": "free-first; paid calls billed", "description": "Shared London Project policy"},
    "none": {"label": "No image", "price": "$0/image", "description": "Use when no relevant image is needed"},
}

DEFAULT_TEXT_MODEL = "gpt-5-mini"
DEFAULT_IMAGE_MODEL = "auto"


def require_text_model(model: str) -> str:
    if model not in TEXT_MODELS:
        raise ValueError("지원하지 않는 글쓰기 엔진입니다")
    return model


def require_image_model(model: str) -> str:
    if model not in IMAGE_MODELS:
        raise ValueError("지원하지 않는 이미지 엔진입니다")
    return model
