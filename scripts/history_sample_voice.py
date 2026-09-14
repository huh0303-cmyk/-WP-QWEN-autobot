"""One explicitly approved sample; no publication and no automatic retries."""
import os, json, base64, urllib.request
from pathlib import Path

TEXT = '''September sixth. One day on the calendar. Three stories that changed lives across the world. Today, we travel backward through history, from a presidential crisis in America, to a revolutionary figure in France, and finally to a ship returning to Spain.

First stop: Buffalo, New York, in nineteen oh one. On September sixth, President William McKinley was shot while attending the Pan American Exposition. The fair became the setting for a national crisis. Historical images help us picture the period, but a portrait or a film of a public appearance is not footage of the attack itself.

McKinley died on September fourteenth, eight days later. Vice President Theodore Roosevelt then became president. Remember the distinction: September sixth marks the shooting, not the day Roosevelt took office. A short timeline keeps the event and its consequences separate.

Now turn the clock back to France, in seventeen fifty seven. September sixth was the birthday of the Marquis de Lafayette. He would later become a general in the American Revolutionary War and a prominent figure in the French Revolution. His life connected political struggles on opposite sides of the Atlantic.

The surviving portrait is a later engraving, not a scene from his birth. Its value is different: it shows how Lafayette was remembered. Paired with dates and context, an old image becomes a doorway into a larger story, rather than an illustration that pretends to record every moment.

Our final stop is Spain, in fifteen twenty two. On September sixth, Victoria returned to Sanlucar de Barrameda, completing the first circumnavigation of the Earth. Ferdinand Magellan had begun the expedition in fifteen nineteen, but did not return. Juan Sebastian Elcano commanded Victoria on the final part of the voyage.

Watch the animated journey close its circle. This is a schematic, not the precise sailing route. The arrival in Spain brought an extraordinary voyage to its conclusion. Remembering both Magellan and Elcano helps distinguish the expedition's beginning from the people who completed it.

Three moments, one date: September sixth. A president attacked, a future revolutionary born, and a voyage around the world completed. History moves backward in this episode, but every story leaves questions for the present. This is Today in History.'''
assert len(TEXT)<6000
key=os.environ['ELEVENLABS_API_KEY']
def request(path, payload=None):
 req=urllib.request.Request('https://api.elevenlabs.io/v1/'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'xi-api-key':key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
voices=request('voices')['voices']
voice=next((v for v in voices if v.get('category')=='premade' and v.get('name','').lower()=='adam'),None)
if voice is None:
 voice=next((v for v in voices if v.get('category')=='premade' and v.get('labels',{}).get('gender')=='male'),None)
if voice is None:raise RuntimeError('No verified stock male narrator available; no cloned voice fallback')
out=Path('history_sample_voice');out.mkdir(exist_ok=True)
data=request('text-to-speech/'+voice['voice_id']+'/with-timestamps',{'text':TEXT,'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.65,'similarity_boost':0.75,'style':0.15,'use_speaker_boost':True}})
(out/'voice.mp3').write_bytes(base64.b64decode(data.pop('audio_base64')))
(out/'alignment.json').write_text(json.dumps(data),encoding='utf-8')
(out/'script.txt').write_text(TEXT,encoding='utf-8')
(out/'metadata.json').write_text(json.dumps({'provider':'ElevenLabs','voice':voice['name'],'characters':len(TEXT),'model':'eleven_multilingual_v2'}),encoding='utf-8')
print('Approved sample audio generated; no public upload.')
