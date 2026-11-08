"""Prevent silent regression of the five playlists and ten language Shorts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PLAYLISTS = ('globalmusic','healing','starbucks','mbb','kpop')
LANGUAGES = ('korean','english','japanese','chinese','vietnamese','spanish','french','german','italian','portuguese')

def audit(root=ROOT):
    errors=[]
    config=json.loads((root/'config/youtube_channels.json').read_text(encoding='utf-8'))
    channels={c['channel_key']:c for c in config['channels']}
    for key in PLAYLISTS:
        if key not in channels:
            errors.append(f'{key}: missing registry entry')
            continue
        c=channels[key]
        if not c.get('enabled',True): errors.append(f'{key}: disabled in registry')
        workflow=c.get('workflow','')
        if not (root/'.github/workflows'/workflow).is_file():
            errors.append(f'{key}: registered workflow missing: {workflow}')
    language=root/'.github/workflows/youtube-language-adjectives-daily.yml'
    if not language.is_file(): errors.append('language: daily Shorts workflow missing')
    else:
        text=language.read_text(encoding='utf-8')
        for phrase in ('scripts/publish_survival_adjective_shorts.py','cancel-in-progress: false','FISH_AUDIO_API_KEY'):
            if phrase not in text: errors.append(f'language: missing guard {phrase}')
    return errors

if __name__=='__main__':
    problems=audit()
    print(json.dumps({'playlists':PLAYLISTS,'languages':LANGUAGES,'issues':problems},indent=2))
    raise SystemExit(bool(problems))
