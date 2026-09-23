"""Bounded provider recovery, exclusively for the two approved newsrooms."""
import os,json
from urllib.parse import urlparse
import requests
from openai_text import openai_generate_text
_failed=set()
last_model=None

def enabled():
 return os.getenv('NEWSROOM_PAID_TEXT_APPROVED','').lower()=='true' and urlparse(os.getenv('TARGET_SITE_URL','')).hostname in {'koreanews365.com','theseouljournal.com'}

def generate(prompt,temperature=0.0):
 global last_model
 if not enabled():raise RuntimeError('newsroom_provider_scope_required')
 if os.getenv('OPENAI_MODEL','')!='gpt-5-mini':raise RuntimeError('newsroom_mini_model_required')
 for model in ('gpt-5-mini','gemini-2.5-flash-lite','gemini-2.5-flash'):
  if model in _failed:continue
  try:
   if model=='gpt-5-mini':
    text=openai_generate_text(prompt,temperature=temperature,max_retries=1,timeout=120)
   else:
    key=os.getenv('GEMINI_API_KEY','').strip()
    if not key:raise RuntimeError('gemini_credentials_missing')
    cfg={'temperature':temperature,'maxOutputTokens':8192}
    if model=='gemini-2.5-flash':cfg['thinkingConfig']={'thinkingBudget':0}
    r=requests.post('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',headers={'x-goog-api-key':key},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':cfg},timeout=120)
    r.raise_for_status();data=r.json();c=(data.get('candidates') or [{}])[0]
    if c.get('finishReason')!='STOP':raise ValueError('incomplete_response')
    text=''.join(x.get('text','') for x in c.get('content',{}).get('parts',[]))
   if not text.strip():raise ValueError('empty_response')
   last_model=model
   from pathlib import Path
   p=Path('artifacts/newsroom-provider-usage.jsonl');p.parent.mkdir(exist_ok=True)
   with p.open('a') as f:f.write(json.dumps({'model':model,'role':'writer_or_independent_review','usage':data.get('usageMetadata',{}) if model!='gpt-5-mini' else {},'billing':'existing project billing; approved newsroom only'})+'\n')
   return text
  except (requests.RequestException,RuntimeError) as exc:
   _failed.add(model);print('Newsroom provider unavailable: '+model+' '+type(exc).__name__)
 raise RuntimeError('newsroom_providers_unavailable')
