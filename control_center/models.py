from __future__ import annotations

TEXT_MODELS = {
    "gemini-2.5-flash-lite": {"label": "Gemini 2.5 Flash-Lite", "price": "$0.0007/글", "description": "일반 글 · 최저비용"},
    "gemini-2.5-flash": {"label": "Gemini 2.5 Flash", "price": "$0.0041/글", "description": "비자·금융·의료 검토"},
    "gpt-5-mini": {"label": "GPT-5 mini", "price": "$0.0033/글", "description": "Gemini 실패·품질미달 시 재작성"},
    "gpt-5.4-mini": {"label": "GPT-5.4 mini", "price": "$0.0075/글", "description": "최중요 글"},
}

IMAGE_MODELS = {
    "none": {"label": "이미지 없음", "price": "$0/장", "description": "관련 이미지가 필요 없을 때"},
    "black-forest-labs/flux-schnell": {"label": "FLUX.1 Schnell", "price": "$0.003/장", "description": "기본 · 빠른 실사 이미지"},
    "bytedance/sdxl-lightning-4step": {"label": "SDXL-Lightning 4-step", "price": "Replicate 사용량", "description": "FLUX 실패 시 2차"},
    "jyoung105/sdxl-turbo": {"label": "SDXL Turbo", "price": "Replicate 사용량", "description": "최종 이미지 대체"},
}

DEFAULT_TEXT_MODEL = "gemini-2.5-flash"
DEFAULT_IMAGE_MODEL = "black-forest-labs/flux-schnell"


def require_text_model(model: str) -> str:
    if model not in TEXT_MODELS:
        raise ValueError("지원하지 않는 글쓰기 엔진입니다")
    return model


def require_image_model(model: str) -> str:
    if model not in IMAGE_MODELS:
        raise ValueError("지원하지 않는 이미지 엔진입니다")
    return model
