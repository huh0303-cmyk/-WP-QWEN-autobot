"""Bounded article writer for the revenue publishing pipeline.

Use Gemini Flash first. If Gemini is unavailable/rate-limited, allow exactly
one GPT-5 mini fallback when OPENAI_ENABLED=true and a configured key exists.
Paid image generation remains disabled; this change affects text only."""

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
    global _gemini_unavailable, last_writer_model

    # The two newsrooms keep their existing explicit recovery path.
    from urllib.parse import urlparse
    target = urlparse(os.getenv('TARGET_SITE_URL', '')).hostname
    if os.getenv('NEWSROOM_PAID_TEXT_APPROVED', '').lower() == 'true' and target in {'koreanews365.com', 'theseouljournal.com'}:
        if os.getenv('OPENAI_MODEL', '') != 'gpt-5-mini':
            raise RuntimeError('Newsroom paid exception permits gpt-5-mini only')
        import newsroom_provider_recovery as recovery
        text = recovery.generate(prompt, temperature=temperature)
        last_writer_model = recovery.last_model
        return text

    last_exc = None
    # Normal network articles: prefer free Gemini, but do not let a 429 leave
    # a revenue site empty for the entire day.
    if not force_gpt:
        for attempt in range(2):
            if _article_attempts is not None:
                _article_attempts.add('gemini')
            try:
                return _try_gemini(prompt, temperature)
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_exc = exc
                print(f'Gemini Flash unavailable or incomplete (attempt {attempt + 1}/2): {_failure_summary(exc)}')

    # One bounded GPT-5 mini fallback. No recursive retries, no image spend.
    try:
        from openai_text import openai_available, openai_generate_text
        if not openai_available():
            raise RuntimeError('OpenAI fallback is not configured/enabled')
        if os.getenv('OPENAI_MODEL', 'gpt-5-mini') != 'gpt-5-mini':
            raise RuntimeError('Daily article fallback permits gpt-5-mini only')
        if _article_attempts is not None:
            _article_attempts.add('openai:gpt-5-mini')
        text = openai_generate_text(prompt, temperature=temperature, max_retries=1, timeout=90)
        last_writer_model = 'gpt-5-mini'
        receipt = Path('artifacts/article-writer-usage.jsonl')
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with receipt.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(),
                'provider': 'openai', 'model': 'gpt-5-mini',
                'billing': 'bounded one-call fallback after Gemini failure'}) + '\n')
        print('Article writer fallback: gpt-5-mini; one bounded call')
        return text
    except Exception as exc:
        if last_exc is None:
            last_exc = exc
        safe_reason = str(exc).replace(os.getenv('OPENAI_API_KEY',''), '[redacted]')[:180]
        print(f'GPT-5 mini fallback unavailable: {type(exc).__name__}: {safe_reason}')
        raise RuntimeError(f'WRITERS_EXHAUSTED: Gemini and bounded GPT-5 mini fallback failed ({type(exc).__name__}: {safe_reason})') from last_exc

