#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openai_text.py
─────────────────────────────────────────────────────────────
ChatGPT(OpenAI) 텍스트 생성 공용 헬퍼. 2026-08-17 "대수술" 결정 —
Gemini 텍스트 생성 대신 여기로 라우팅한다(이미지/영상은 그대로 Gemini 유지,
비용 주범이 아니었던 걸로 확인됨). OPENAI_API_KEY가 설정돼 있으면 이 모듈이
쓰이고, 없으면 각 스크립트가 기존 Gemini 경로로 폴백한다 — 그래서 이 파일이
없거나 키가 없어도 기존 파이프라인은 그대로 돌아간다.

모델명은 계속 바뀌므로 하드코딩하지 않고 환경변수로 오버라이드 가능하게
해둠(기본값은 2026-08 기준 가장 저렴한 축인 gpt-4o-mini).
"""
import os

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def openai_available():
    return bool(OPENAI_API_KEY)


def openai_generate_text(prompt, temperature=0.9, max_retries=5):
    """curio_longform.py의 gemini_generate_text와 동일한 계약(플레인 텍스트
    문자열 반환, 실패시 RuntimeError) — 호출부를 바꾸지 않고 내부 구현만
    바꿔치기할 수 있게 시그니처를 맞췄다."""
    import time as _time

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    last_err = None
    for attempt in range(max_retries):
        r = requests.post(OPENAI_URL, headers=headers, json=body, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            last_err = f"{r.status_code}: {r.text[:200]}"
            wait = min(15 * (2 ** attempt), 120)
            _time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"OpenAI 텍스트 생성 최종 실패({max_retries}회 재시도 후): {last_err}")
