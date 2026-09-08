"""ElevenLabs-only vocabulary speech; cache each phrase before local repetition.

No automatic retries: an ambiguous paid API response must be investigated.
This module generates clips, not social posts or scheduled jobs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'config/vocabulary_cards.json'


def synthesize(text, language, cache_dir, *, config_path=DEFAULT_CONFIG, opener=None):
    settings = json.loads(Path(config_path).read_text(encoding='utf-8'))['tts']
    if settings['provider'] != 'elevenlabs' or settings.get('fallback_provider'):
        raise ValueError('Vocabulary cards require ElevenLabs without fallback')
    if language not in settings['languages'] or not text.strip():
        raise ValueError('Unsupported language or empty text')
    payload = dict(text=text, model_id=settings['model_id'], language_code=language,
                   voice_settings=settings['voice_settings'])
    identity = dict(provider='ElevenLabs', voice_id=settings['voice_id'],
                    output_format='mp3_44100_128', payload=payload)
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = Path(cache_dir)
    folder.mkdir(parents=True, exist_ok=True)
    audio_path, receipt_path = folder / f'{digest}.mp3', folder / f'{digest}.json'
    if audio_path.exists() or receipt_path.exists():
        if not audio_path.exists() or not receipt_path.exists():
            raise RuntimeError('Incomplete audio cache; inspect before generating again')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if hashlib.sha256(audio_path.read_bytes()).hexdigest() != receipt['sha256']:
            raise RuntimeError('Audio cache checksum mismatch')
        return audio_path
    if not settings['paid_generation_enabled']:
        raise RuntimeError('ElevenLabs speech generation is disabled')
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key:
        raise RuntimeError('ELEVENLABS_API_KEY is required; no silent fallback')
    # Exclusive marker prevents simultaneous or ambiguous duplicate billing.
    pending = folder / f'{digest}.pending'
    with pending.open('x', encoding='utf-8') as marker:
        marker.write('Generation requested. Inspect any failure before removing this marker.')
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{settings['voice_id']}?output_format=mp3_44100_128",
        data=json.dumps(payload).encode(),
        headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
    try:
        with (opener or urllib.request.urlopen)(request, timeout=120) as response:
            audio = response.read()
            cost = response.headers.get('character-cost')
        if len(audio) < 100:
            raise RuntimeError('ElevenLabs returned empty or incomplete audio')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'ElevenLabs HTTP {exc.code}; no retry or voice fallback') from None
    audio_path.write_bytes(audio)
    receipt = dict(identity, characters=len(text), character_cost=cost,
                   sha256=hashlib.sha256(audio).hexdigest())
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    pending.unlink()
    return audio_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', required=True)
    parser.add_argument('--word', required=True)
    parser.add_argument('--sentence', required=True)
    parser.add_argument('--cache-dir', required=True)
    args = parser.parse_args()
    for role, text in [('word', args.word), ('sentence', args.sentence)]:
        path = synthesize(text, args.language, args.cache_dir)
        print(f'{role}: {path}')


if __name__ == '__main__':
    main()
