#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude (Anthropic) text helper — Tistory 5개 사이트 전용 작가 엔진.

openai_text.py와 동일한 안전 패턴을 따른다:
- ANTHROPIC_API_KEY가 있다는 이유만으로 자동 사용하지 않는다.
- CLAUDE_ENABLED=true를 명시한 실행에서만 사용한다.
- 크레딧/한도 소진(429)은 재시도로 회복되지 않으므로 즉시 중단한다.
"""
import os
import time

import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
CLAUDE_ENABLED = os.environ.get("CLAUDE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "8000"))


def claude_available():
    """Claude는 키 + 명시적 활성화가 둘 다 있을 때만 사용한다."""
    return bool(ANTHROPIC_API_KEY) and CLAUDE_ENABLED


def claude_generate_text(prompt, system=None, temperature=0.9, max_retries=5):
    if not claude_available():
        raise RuntimeError("Claude generation is disabled; use the caller's fallback")

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        # Sonnet 5 (this repo's default CLAUDE_MODEL) removed sampling
        # params entirely - temperature/top_p/top_k all return 400. The
        # `temperature` argument is kept for caller compatibility but
        # deliberately not sent.
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    last_err = None
    for attempt in range(max_retries):
        r = requests.post(CLAUDE_URL, headers=headers, json=body, timeout=120)
        if r.status_code == 429:
            # credit_balance_too_low / rate_limit_error 둘 다 429로 온다.
            # 잔액 고갈은 재시도해도 회복되지 않으므로 즉시 중단한다.
            if "credit" in r.text.lower() or "balance" in r.text.lower():
                raise RuntimeError(f"Claude unavailable (credit balance): {r.status_code}")
            last_err = f"{r.status_code}: {r.text[:200]}"
            time.sleep(min(15 * (2 ** attempt), 120))
            continue
        if r.status_code >= 500:
            last_err = f"{r.status_code}: {r.text[:200]}"
            time.sleep(min(15 * (2 ** attempt), 120))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Claude request failed: {r.status_code}: {r.text[:500]}")
        r.raise_for_status()
        parts = r.json().get("content", [])
        text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        return text.strip()
    raise RuntimeError(f"Claude 텍스트 생성 최종 실패({max_retries}회 재시도 후): {last_err}")
