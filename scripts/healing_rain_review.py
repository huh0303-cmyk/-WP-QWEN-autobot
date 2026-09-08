"""Owner-requested 75-minute synthetic rain review; private only, text-free art."""
import json, os, secrets, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
import youtube_publish_approved as publisher
from automation_hub.youtube_identity import verify_authenticated_channel
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageOps
WORK = ROOT/'data/healing-rain-review'
WORK.mkdir(parents=True, exist_ok=True)
MARKER = 'Review reference: healing-rain-75-20260908'
DURATION = 4500
TITLE = 'Gentle Jungle Rain | 75 Minutes of Peaceful Forest Ambience, No Music'
DESCRIPTION = '''Step beneath a lush green canopy and settle into 75 minutes of gentle rain. Broad tropical leaves, soft forest mist, and a quiet stream create an open, peaceful setting for reading, resting, journaling, or an unhurried evening at home.

This soundscape was newly synthesized for this video. Layers of softly filtered rain-like noise create a continuous stereo texture with gentle changes in intensity. It is not a recording made in a real jungle, and no existing songs or short repeating rain recordings were used. There is no music, narration, or sudden thunder.

The forest artwork stays free of titles and captions so the scene can remain calm and uncluttered. Start at a comfortable volume and adjust it to suit your room or headphones. You can leave the sound in the background while you read, work quietly, or take a break.

Thank you for spending a little time in this rainy green retreat. This private sample is prepared for the channel owner's review before any public release.

'''+MARKER

def save(name, value):
    (WORK/name).write_text(json.dumps(value, indent=2), encoding='utf-8')

def ff(*args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)

def render():
    image = ImageOps.fit(Image.open(ROOT/'assets/playlist-review/healing-rainforest.png').convert('RGB'),(1920,1080))
    image.save(WORK/'thumbnail.jpg', quality=90)
    ff('-loop','1','-framerate','1','-i',WORK/'thumbnail.jpg','-t','10','-c:v','libx264','-preset','fast','-tune','stillimage','-pix_fmt','yuv420p','-r','1',WORK/'scene.mp4')
    seeds = [secrets.randbelow(2147483646)+1 for _ in range(2)]
    save('synthesis.json',{'seconds':4500,'source':'new continuous procedural stereo rain','seeds':seeds,'reused_audio':False,'thumbnail_text':False})
    # Independent continuous noise generators: no looped audio segment.
    filters = ';'.join([
        '[1:a]highpass=f=250,lowpass=f=7500,volume=0.7*(0.92+0.08*sin(t/29)):eval=frame[l]',
        '[2:a]highpass=f=180,lowpass=f=6800,volume=0.7*(0.92+0.08*sin(t/37)):eval=frame[r]',
        '[l][r]join=inputs=2:channel_layout=stereo,afade=t=in:d=4,afade=t=out:st=4494:d=6[a]'])
    ff('-stream_loop','-1','-i',WORK/'scene.mp4','-f','lavfi','-i',f'anoisesrc=color=pink:sample_rate=48000:amplitude=0.65:seed={seeds[0]}',
       '-f','lavfi','-i',f'anoisesrc=color=pink:sample_rate=48000:amplitude=0.65:seed={seeds[1]}',
       '-filter_complex',filters,'-map','0:v','-map','[a]','-t','4500','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',WORK/'rain-75.mp4')
    seconds = float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(WORK/'rain-75.mp4')]))
    if abs(seconds-4500)>2: raise RuntimeError(f'Incorrect duration: {seconds}')
    ff('-ss','30','-i',WORK/'rain-75.mp4','-t','20','-c','copy',WORK/'preview.mp4')
    print('RENDERED',seconds,flush=True)

def main():
    service = publisher.get_youtube_service()
    actual = verify_authenticated_channel(service,'healing')
    if actual != 'UC7yEsLM-HoXudngrD-4FIqg': raise RuntimeError('Healing channel lock mismatch')
    uploads=service.channels().list(part='contentDetails',mine=True).execute()['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    ids=[]; token=None
    while True:
        page=service.playlistItems().list(part='contentDetails',playlistId=uploads,maxResults=50,pageToken=token).execute()
        ids.extend(v['contentDetails']['videoId'] for v in page.get('items',[]))
        token=page.get('nextPageToken')
        if not token: break
    matches=[]
    for offset in range(0,len(ids),50):
        matches.extend(v for v in service.videos().list(part='snippet,status',id=','.join(ids[offset:offset+50])).execute().get('items',[]) if MARKER in v['snippet'].get('description',''))
    if len(matches)>1: raise RuntimeError('Duplicate review markers need inspection')
    if matches:
        video_id=matches[0]['id']
        if matches[0]['status']['privacyStatus']!='private': raise RuntimeError('Existing sample privacy changed')
        # Preserve the existing thumbnail when resuming a previously uploaded motion sample.
    else:
        render()
        video_id=publisher.upload_to_youtube(service,str(WORK/'rain-75.mp4'),None,TITLE,DESCRIPTION,['nature sounds','forest ambience','no music','relaxation'])
    save('upload.json',{'video_id':video_id,'channel_id':actual,'privacy':'private'})
    if (WORK/'thumbnail.jpg').exists(): service.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(WORK/'thumbnail.jpg'))).execute()
    for _ in range(90):
        video=service.videos().list(part='snippet,status,processingDetails,contentDetails',id=video_id).execute()['items'][0]
        save('verified-status.json',video)
        if video['status']['privacyStatus']!='private' or video['snippet']['channelId']!=actual: raise RuntimeError('Upload identity/privacy mismatch')
        state=video.get('processingDetails',{}).get('processingStatus')
        if state=='succeeded':
            import re
            duration=video['contentDetails']['duration']
            parts=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',duration)
            actual_seconds=sum(int(v or 0)*m for v,m in zip(parts.groups(),(3600,60,1))) if parts else -1
            if abs(actual_seconds-DURATION)>2: raise RuntimeError('Unexpected uploaded duration')
            print('PRIVATE_UPLOAD_VERIFIED',video_id,flush=True); return
        if state in ('failed','terminated'): raise RuntimeError('YouTube processing '+state)
        time.sleep(10)
    raise RuntimeError('Upload exists, YouTube processing remains pending; do not blindly upload again')

if __name__=='__main__': main()
