"""Randomly try one of the two approved writers first this article, then one
fallback attempt with the other if the first fails. No hidden HTTP retry loop."""
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
import requests
from openai_text import openai_available, openai_generate_text

_gemini_unavailable = False
_gpt_unavailable = False
last_writer_model = 'not_called'
_article_attempts = None


def begin_article():
    global _article_attempts, _gemini_unavailable, _gpt_unavailable, last_writer_model
    _article_attempts = set()
    _gemini_unavailable = _gpt_unavailable = False
    last_writer_model = 'not_called'


def _try_gemini(prompt, temperature):
    global last_writer_model
    key = os.getenv('GEMINI_API_KEY', '').strip()
    model = os.getenv('ARTICLE_GEMINI_MODEL', 'gemini-2.5-flash')
    if not key or _gemini_unavailable:
        raise RuntimeError('Gemini Flash not configured or already failed once this process')
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
            'billing': 'Actual project billing applies; not assumed free'}) + '\n')
    print(f'Article writer: {model}; one completed call')
    last_writer_model = model
    return text.strip()


def _try_gpt(prompt, temperature):
    global last_writer_model
    if not openai_available() or _gpt_unavailable:
        raise RuntimeError('OPENAI_API_KEY not configured or already failed once this process')
    print('Article writer: GPT; maximum one attempt')
    last_writer_model = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
    # Long articles repeatedly exceeded 120s in live WP/Blogger runs. Await the
    # same request longer rather than paying for a second generated article.
    return openai_generate_text(prompt, temperature=temperature, max_retries=1, timeout=300)


def generate_text(prompt, temperature=0.7, force_gpt=False, repair=False):
    global _gemini_unavailable, _gpt_unavailable
    # 2026-09-12 (user directive): randomly pick which of the two approved
    # writers goes first for THIS article instead of always trying Gemini
    # Flash first, so the load is split between both instead of GPT sitting
    # idle as a pure backup. Whichever one is not picked is the automatic
    # fallback if the first attempt fails technically. Quality repairs try
    # the other writer first, then retain the available writer on provider outage.
    if force_gpt:
        order = ['gpt', 'gemini']
    elif repair and last_writer_model != 'not_called':
        previous = 'gemini' if last_writer_model.startswith('gemini') else 'gpt'
        order = ['gpt', 'gemini'] if previous == 'gemini' else ['gemini', 'gpt']
        print('Quality repair: switching writer from ' + previous + ' to ' + order[0])
    else:
        order = random.sample(['gemini', 'gpt'], 2)
    last_exc = None
    for provider in order:
        if _article_attempts is not None:
            if provider in _article_attempts:
                continue
            _article_attempts.add(provider)
        try:
            if provider == 'gemini':
                return _try_gemini(prompt, temperature)
            return _try_gpt(prompt, temperature)
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_exc = exc
            if provider == 'gemini':
                _gemini_unavailable = True
                print(f'Gemini Flash unavailable or incomplete; falling back to GPT: {type(exc).__name__}')
            else:
                _gpt_unavailable = True
                print(f'GPT unavailable; falling back to Gemini Flash: {type(exc).__name__}')
    raise RuntimeError('WRITERS_EXHAUSTED: both approved writers attempted; retain draft and stop this article')
