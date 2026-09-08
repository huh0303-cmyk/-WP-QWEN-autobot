"""Owner-requested vocabulary voice replacement. Never uploads or prints keys."""
import json, os, urllib.request, urllib.error, hashlib
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

if os.environ.get('GENERATE_VOCABULARY') == 'true':
    # Verified ElevenLabs default George ID from the official API quickstart.
    voice_id='JBFqnCBsd6RMkjVDRZzb'
    model='eleven_flash_v2_5'
    lessons={'ko':['학교','학교에 가요.'],'en':['school','I go to school.'],'de':['Schule','Ich gehe zur Schule.']}
    manifest=[]
    for lang,texts in lessons.items():
        for i,text in enumerate(texts):
            payload={'text':text,'model_id':model,'language_code':lang,'voice_settings':{'stability':0.65,'similarity_boost':0.75,'speed':0.85}}
            path=OUT/f'{lang}-speech-{i}.mp3'
            req=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128',data=json.dumps(payload).encode(),headers={'xi-api-key':KEY,'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=120) as r:
                    audio=r.read();credits=r.headers.get('character-cost')
            except urllib.error.HTTPError as e:
                detail=e.read().decode(errors='replace').replace(KEY,'[REDACTED]')
                print('Generation stopped:',e.code,detail[:1000])
                raise SystemExit(1)
            if len(audio)<100:raise RuntimeError('Unexpected empty audio')
            path.write_bytes(audio)
            manifest.append({'language':lang,'text':text,'file':path.name,'provider':'ElevenLabs','voice':'George','voice_id':voice_id,'model_id':model,'characters':len(text),'billed_character_cost':credits,'sha256':hashlib.sha256(audio).hexdigest()})
            (OUT/'generation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Generated',lang,i,len(text),'characters')
    print('Six speech clips generated once each. Repeat locally; no external publication.')
    raise SystemExit(0)

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
