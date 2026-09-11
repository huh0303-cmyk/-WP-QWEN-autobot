"""One Flash attempt, then one GPT attempt. No hidden HTTP retry loop."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests
from openai_text import openai_available, openai_generate_text

_unavailable = False
last_writer_model = 'not_called'


def generate_text(prompt, temperature=0.7, force_gpt=False):
    global _unavailable, last_writer_model
    key = os.getenv('GEMINI_API_KEY', '').strip()
    model = os.getenv('ARTICLE_GEMINI_MODEL', 'gemini-2.5-flash')
    if key and not _unavailable and not force_gpt:
        try:
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
        except (requests.RequestException, ValueError):
            # Once unavailable, avoid repeatedly probing a broken/quota-limited model in this process.
            _unavailable = True
            print('Flash unavailable or incomplete; one GPT fallback allowed')
    if not openai_available():
        raise RuntimeError('No available article writer; preserve the job for retry')
    print('Article writer: GPT fallback; maximum one attempt')
    last_writer_model = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
    # Long articles repeatedly exceeded 120s in live WP/Blogger runs. Await the
    # same request longer rather than paying for a second generated article.
    return openai_generate_text(prompt, temperature=temperature, max_retries=1, timeout=300)
