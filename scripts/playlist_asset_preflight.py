"""Read-only channel identity and approved asset inventory before rendering."""
import json, os, sys
from pathlib import Path
os.environ['CHANNEL_KEY']=sys.argv[1]
required=('GOOGLE_OAUTH_CLIENT_ID','GOOGLE_OAUTH_CLIENT_SECRET','GOOGLE_OAUTH_REFRESH_TOKEN')
missing=[name for name in required if not os.environ.get(name)]
if missing:raise SystemExit('Missing GitHub Actions environment credentials: '+', '.join(missing))
import youtube_playlist_maker as maker
from collections import Counter
service=maker.base.get_drive_service()
tracks=maker._bank_list(service,maker.base.MUSIC_SOURCE_FOLDER_ID,maker.base.AUDIO_EXTS,'audio/')
images=maker._bank_list(service,maker.base.THUMBNAIL_FOLDER_ID,maker.base.IMAGE_EXTS,'image/')
print(json.dumps({'channel':sys.argv[1], 'audio_names':[t['name'] for t in tracks], 'image_names':[t['name'] for t in images]},ensure_ascii=False))
upper=sys.argv[1].upper()
for key in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN'):
 value=os.environ.get('YOUTUBE_OAUTH_'+key+'_'+upper)
 if value:os.environ['YOUTUBE_OAUTH_'+key]=value
import youtube_publish_approved as publisher
from automation_hub.youtube_identity import verify_authenticated_channel
verify_authenticated_channel(publisher.get_youtube_service(),sys.argv[1])
print('Channel identity verified')
