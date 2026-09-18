"""Free-tier only: every article goes through Gemini Flash (free tier). Paid
GPT-5 mini writing is fully disabled per 2026-09-18 user directive -- no paid
text generation anywhere in this pipeline, and no fallback to it."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

_gemini_unavailable = False
last_writer_model = 'not_called'
_article_attempts = None


def _failure_summary(exc):
    """Return a useful provider diagnosis without logging keys or response bodies."""
    response = getattr(exc, 'response', None)
    status = getattr(response, 'status_code', None)
    if status:
        return f'{type(exc).__name__} HTTP {status}'
    return type(exc).__name__


def begin_article():
    global _article_attempts, _gemini_unavailable, last_writer_model
    _article_attempts = set()
    _gemini_unavailable = False
    last_writer_model = 'not_called'


def _try_gemini(prompt, temperature):
    global last_writer_model
    key = os.getenv('GEMINI_API_KEY', '').strip()
    model = os.getenv('ARTICLE_GEMINI_MODEL', 'gemini-2.5-flash')
    if not key:
        raise RuntimeError('Gemini Flash not configured (GEMINI_API_KEY missing)')
    response = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        headers={'x-goog-api-key': key}, timeout=120,
        json={'contents': [{'parts': [{'text': prompt}]}],
              'generationConfig': {'temperature': temperature, 'maxOutputTokens': 8192,
                                   'thinkingConfig': {'thinkingBudget': 0}}})
    response.raise_for_status()
    data = response.json()
    candidate = (data.get('candidates') or [{}])[0]
    text = ''.join(p.get('text', '') for p in candidate.get('content', {}).get('parts', []))
    if candidate.get('finishReason') != 'STOP' or not text.strip():
        raise ValueError('Flash did not return a complete response')
    receipt = Path('artifacts/article-writer-usage.jsonl')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(),
            'provider': 'gemini', 'model': model, 'usage': data.get('usageMetadata', {}),
            'billing': 'Free tier (Gemini Flash); paid GPT text generation is disabled'}) + '\n')
    print(f'Article writer: {model}; one completed call')
    last_writer_model = model
    return text.strip()


def generate_text(prompt, temperature=0.7, force_gpt=False, repair=False):
    global _gemini_unavailable
    # 2026-09-18 (user directive): paid GPT is fully disabled, even as a
    # fallback. Only the free Gemini Flash tier writes articles now. The
    # force_gpt/repair arguments are kept for call-site compatibility but no
    # longer select a paid provider -- they only affect retry framing below.
    last_exc = None
    for attempt in range(2):
        if _article_attempts is not None:
            _article_attempts.add('gemini')
        try:
            return _try_gemini(prompt, temperature)
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_exc = exc
            _gemini_unavailable = False
            print(f'Gemini Flash unavailable or incomplete (attempt {attempt + 1}/2), retrying free tier only: {_failure_summary(exc)}')
    raise RuntimeError('WRITERS_EXHAUSTED: Gemini Flash failed twice and paid GPT is disabled by policy; retain draft and stop this article') from last_exc
