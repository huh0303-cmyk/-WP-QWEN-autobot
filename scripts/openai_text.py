#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI text/image helper.

2026-08-26 safety change:
- OPENAI_API_KEY가 저장돼 있다는 이유만으로 유료 OpenAI 경로를 자동 선택하지 않는다.
- OPENAI_ENABLED=true를 명시한 실행에서만 OpenAI를 사용한다.
- 기본값은 Gemini/기존 무료·보유 경로로 폴백한다.
이렇게 하면 잔액 0인 OpenAI 키 때문에 전체 WordPress/뉴스 파이프라인이 429로
중단되는 문제를 막을 수 있다.
"""
import base64
import os
import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_ENABLED = os.environ.get("OPENAI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"


def openai_available():
    """OpenAI는 키 + 명시적 활성화가 둘 다 있을 때만 사용한다."""
    return bool(OPENAI_API_KEY) and OPENAI_ENABLED


def openai_generate_text(prompt, temperature=0.9, max_retries=5):
    import time as _time
    if not openai_available():
        raise RuntimeError("OpenAI generation is disabled; use the caller's Gemini fallback")

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    send_temperature = not OPENAI_MODEL.startswith("gpt-5")

    def _body(with_temp):
        b = {"model": OPENAI_MODEL, "messages": [{"role": "user", "content": prompt}]}
        if with_temp:
            b["temperature"] = temperature
        return b

    last_err = None
    for attempt in range(max_retries):
        r = requests.post(OPENAI_URL, headers=headers, json=_body(send_temperature), timeout=60)
        if r.status_code == 400 and send_temperature and "temperature" in r.text.lower():
            send_temperature = False
            r = requests.post(OPENAI_URL, headers=headers, json=_body(False), timeout=60)
        if r.status_code == 429:
            # insufficient_quota/credits는 재시도해도 회복되지 않으므로 즉시 중단.
            if "insufficient" in r.text.lower() or "credit" in r.text.lower() or "quota" in r.text.lower():
                raise RuntimeError(f"OpenAI unavailable (quota/credits): {r.status_code}")
            last_err = f"{r.status_code}: {r.text[:200]}"
            _time.sleep(min(15 * (2 ** attempt), 120))
            continue
        if r.status_code >= 500:
            last_err = f"{r.status_code}: {r.text[:200]}"
            _time.sleep(min(15 * (2 ** attempt), 120))
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"OpenAI 텍스트 생성 최종 실패({max_retries}회 재시도 후): {last_err}")


_image_model_fallback_active = False
_NEXT_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL_FALLBACK", "gpt-image-1.5")


def _looks_like_model_unavailable(status_code, text):
    if status_code == 404:
        return True
    low = text.lower()
    return status_code == 400 and (
        "model" in low and ("not found" in low or "does not exist" in low
                             or "deprecated" in low or "retired" in low)
    )


def openai_generate_image(prompt, out_path, size="1024x1024", max_retries=3):
    import time as _time
    global _image_model_fallback_active
    if not openai_available():
        return False

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    model = _NEXT_IMAGE_MODEL if _image_model_fallback_active else OPENAI_IMAGE_MODEL
    last_err = None
    for attempt in range(max_retries):
        body = {"model": model, "prompt": prompt, "size": size, "n": 1}
        try:
            r = requests.post(OPENAI_IMAGE_URL, headers=headers, json=body, timeout=90)
            if not _image_model_fallback_active and _looks_like_model_unavailable(r.status_code, r.text):
                print(f"  ⚠️ 이미지 모델 '{model}' 사용 불가({r.status_code}) → '{_NEXT_IMAGE_MODEL}'로 자동 전환")
                _image_model_fallback_active = True
                model = _NEXT_IMAGE_MODEL
                continue
            if r.status_code == 429 and ("insufficient" in r.text.lower() or "credit" in r.text.lower() or "quota" in r.text.lower()):
                return False
            if r.status_code == 429 or r.status_code >= 500:
                last_err = f"{r.status_code}: {r.text[:200]}"
                _time.sleep(min(10 * (2 ** attempt), 60))
                continue
            r.raise_for_status()
            b64 = r.json()["data"][0]["b64_json"]
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
        except Exception as e:
            last_err = str(e)[:200]
            _time.sleep(5)
    if last_err:
        print(f"  ⚠️ OpenAI 이미지 생성 실패: {last_err}")
    return False
