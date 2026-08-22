#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openai_text.py
─────────────────────────────────────────────────────────────
ChatGPT(OpenAI) 텍스트/이미지 생성 공용 헬퍼.

2026-08-17 "대수술" 결정 — Gemini 텍스트 생성 대신 여기로 라우팅
(openai_generate_text). OPENAI_API_KEY가 설정돼 있으면 이 모듈이 쓰이고,
없으면 각 스크립트가 기존 Gemini 경로로 폴백한다 — 그래서 이 파일이
없거나 키가 없어도 기존 파이프라인은 그대로 돌아간다.

2026-08-18 확장 — 사용자 지시("API문제 머리아프고 싫어.. 돈들어가는거
OPEN AI써.. 제미나이는 진짜 무료 범위내에서만.. 나노 바나나도"): 이미지
생성도 같은 원칙으로 확장(openai_generate_image, gpt-image-1 사용) —
Gemini 월간 지출한도 초과로 하루 종일 파이프라인이 막혔던 사고 이후,
돈이 드는 생성(텍스트+이미지)은 OpenAI를 우선으로 쓰고 Gemini/Nano
Banana는 OPENAI_API_KEY가 없을 때의 폴백으로만 남긴다.

모델명은 계속 바뀌므로 하드코딩하지 않고 환경변수로 오버라이드 가능하게
해둠(기본값은 2026-08 기준 가장 저렴한 축인 gpt-4o-mini).
"""
import base64
import os

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"


def openai_available():
    return bool(OPENAI_API_KEY)


def openai_generate_text(prompt, temperature=0.9, max_retries=5):
    """curio_longform.py의 gemini_generate_text와 동일한 계약(플레인 텍스트
    문자열 반환, 실패시 RuntimeError) — 호출부를 바꾸지 않고 내부 구현만
    바꿔치기할 수 있게 시그니처를 맞췄다.

    2026-08-17: gpt-5.6 계열은 temperature 커스텀 값을 아예 지원 안 함
    (기본값 1만 허용, 다른 값 주면 400) — 이 모델일 땐 아예 안 보내고,
    혹시 다른 모델로 바뀌어도 안전하게 같은 400을 만나면 temperature
    없이 한 번 더 시도한다."""
    import time as _time

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    send_temperature = not OPENAI_MODEL.startswith("gpt-5.6")

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
        if r.status_code == 429 or r.status_code >= 500:
            last_err = f"{r.status_code}: {r.text[:200]}"
            wait = min(15 * (2 ** attempt), 120)
            _time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"OpenAI 텍스트 생성 최종 실패({max_retries}회 재시도 후): {last_err}")


# 2026-08-22: gpt-image-1이 2026-10-23 지원 종료 예정(사용자 지시: "서비스가
# 종료되면 1.5로 가라는 확실한 조건을 넣어놔"). OPENAI_IMAGE_MODEL 환경변수를
# 그날 수동으로 바꾸는 것과 별개로, 모델이 실제로 죽었을 때(404/모델없음 응답)
# 코드가 스스로 후속 모델로 전환하는 안전망을 追加한다 — autopost_mega.py의
# GEMINI_MODEL_PRIMARY→FALLBACK 자동전환과 동일한 패턴.
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
    """gemini_generate_image(prompt, out_path) -> bool 과 동일한 계약 —
    호출부를 바꾸지 않고 내부 구현만 바꿔치기할 수 있게 시그니처를 맞췄다.
    실패해도 예외를 던지지 않고 False를 반환한다(호출부가 Gemini 폴백으로
    넘어갈 수 있게)."""
    import time as _time
    global _image_model_fallback_active

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    model = _NEXT_IMAGE_MODEL if _image_model_fallback_active else OPENAI_IMAGE_MODEL

    last_err = None
    for attempt in range(max_retries):
        body = {"model": model, "prompt": prompt, "size": size, "n": 1}
        try:
            r = requests.post(OPENAI_IMAGE_URL, headers=headers, json=body, timeout=90)
            if not _image_model_fallback_active and _looks_like_model_unavailable(r.status_code, r.text):
                print(f"  ⚠️ 이미지 모델 '{model}' 사용 불가({r.status_code}) → "
                      f"'{_NEXT_IMAGE_MODEL}'로 자동 전환")
                _image_model_fallback_active = True
                model = _NEXT_IMAGE_MODEL
                continue
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
    return False
