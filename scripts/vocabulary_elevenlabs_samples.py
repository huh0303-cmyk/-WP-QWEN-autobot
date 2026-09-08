"""Owner-requested vocabulary voice replacement. Never uploads or prints keys."""
import json, os, urllib.request, urllib.error
from pathlib import Path

OUT = Path('vocabulary_elevenlabs_samples')
OUT.mkdir(exist_ok=True)
KEY = os.environ['ELEVENLABS_API_KEY']
def get(path):
    req = urllib.request.Request('https://api.elevenlabs.io/v1/' + path, headers={'xi-api-key': KEY})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors='replace').replace(KEY,'[REDACTED]')
        result={'http_status':e.code,'detail':body[:1200]}
        (OUT/(path.replace('/','_')+'-error.json')).write_text(json.dumps(result),encoding='utf-8')
        print(path, result)
        return {}

voices = get('voices').get('voices',[])
models = get('models')
subscription = get('user/subscription')
safe = {
    'voices': [{k:v.get(k) for k in ('voice_id','name','category','labels','verified_languages')} for v in voices],
    'models': [{k:m.get(k) for k in ('model_id','name','languages','token_cost_factor')} for m in (models if isinstance(models,list) else [])],
    'subscription': {k:subscription.get(k) for k in ('tier','character_count','character_limit','can_extend_character_limit')}
}
(OUT/'inventory.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2),encoding='utf-8')
print('ElevenLabs account inspected. No speech generation or publication in inspection mode.')
